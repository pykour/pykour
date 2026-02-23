"""Base query class and type aliases."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Coroutine

if TYPE_CHECKING:
    from pykour.db.access_policy.context import PolicyContextData
    from pykour.db.access_policy.enforcer import BasePolicyEnforcer
    from pykour.db.access_policy.policy import AccessPolicy
    from pykour.db.result import Row


# Type aliases for executor functions
ExecuteFunc = Callable[[str, tuple[Any, ...]], Coroutine[Any, Any, int]]
FetchAllFunc = Callable[[str, tuple[Any, ...]], Coroutine[Any, Any, list["Row"]]]
FetchOneFunc = Callable[[str, tuple[Any, ...]], Coroutine[Any, Any, "Row | None"]]
GetPolicyContextFunc = Callable[[], "PolicyContextData | None"]


class BaseQuery:
    """Base class for query builders."""

    # Set by subclasses before any policy check
    _table: str

    def __init__(
        self,
        execute_func: ExecuteFunc,
        fetch_all_func: FetchAllFunc,
        fetch_one_func: FetchOneFunc,
        *,
        policy_enforcer: "BasePolicyEnforcer | None" = None,
        table_policies: "dict[str, AccessPolicy] | None" = None,
        table_classes: dict[str, type] | None = None,
        get_policy_context: GetPolicyContextFunc | None = None,
    ) -> None:
        self._execute_func = execute_func
        self._fetch_all_func = fetch_all_func
        self._fetch_one_func = fetch_one_func
        self._params: list[Any] = []
        self._policy_enforcer = policy_enforcer
        self._table_policies: "dict[str, AccessPolicy]" = table_policies or {}
        self._table_classes: dict[str, type] = table_classes or {}
        self._get_policy_context = get_policy_context

    def _should_apply_policy(
        self,
    ) -> "tuple[BasePolicyEnforcer, AccessPolicy, PolicyContextData] | None":
        """Check if policy should be applied and return enforcer, policy and context.

        Returns:
            Tuple of (enforcer, policy, context) if policy should be applied, None otherwise.
        """
        if self._policy_enforcer is None or self._get_policy_context is None:
            return None

        context = self._get_policy_context()
        if context is None or context.bypass_enforcement:
            return None

        policy = self._table_policies.get(self._table)
        if policy is None:
            return None

        return self._policy_enforcer, policy, context

    def _add_param(self, value: Any) -> str:
        """Add a parameter and return its placeholder."""
        self._params.append(value)
        return f"${len(self._params)}"

    def _build_where_clause(
        self,
        conditions: dict[str, Any],
        existing_clauses: list[str],
    ) -> list[str]:
        """Build WHERE clause from conditions dict."""
        clauses = existing_clauses.copy()
        for key, value in conditions.items():
            if value is None:
                clauses.append(f"{key} IS NULL")
            else:
                placeholder = self._add_param(value)
                clauses.append(f"{key} = {placeholder}")
        return clauses

    def _process_raw_condition(self, condition: str, args: tuple[Any, ...]) -> str:
        """Process raw SQL condition, replacing $N placeholders.

        Handles out-of-order placeholders (e.g., "$2 > $1") and repeated
        placeholders (e.g., "$1 BETWEEN $1 AND $2") correctly.

        Args:
            condition: SQL condition with $1, $2, ... placeholders.
            args: Values for the placeholders.

        Returns:
            Processed condition with updated placeholder indices.

        Raises:
            ValueError: If a placeholder index is out of range.
        """
        # Find all $N placeholders in the condition
        placeholder_pattern = re.compile(r"\$(\d+)")
        matches = placeholder_pattern.findall(condition)

        if not matches:
            return condition

        # Get unique indices and validate them
        unique_indices = sorted(set(int(m) for m in matches))

        for idx in unique_indices:
            if idx < 1 or idx > len(args):
                raise ValueError(
                    f"Placeholder ${idx} is out of range; "
                    f"expected $1 to ${len(args)} for {len(args)} argument(s)"
                )

        # Build mapping from original $N to new placeholder
        # Process in order of indices to maintain parameter order
        placeholder_map: dict[str, str] = {}
        for idx in unique_indices:
            new_placeholder = self._add_param(args[idx - 1])
            placeholder_map[f"${idx}"] = new_placeholder

        # Replace all occurrences in a single pass using regex substitution
        return placeholder_pattern.sub(
            lambda m: placeholder_map[f"${m.group(1)}"], condition
        )

    # Comparison operator helpers for subclasses
    def _build_comparison(self, column: str, operator: str, value: Any) -> str:
        """Build a comparison clause."""
        placeholder = self._add_param(value)
        return f"{column} {operator} {placeholder}"

    def _build_in_clause(
        self, column: str, values: list[Any], negated: bool = False
    ) -> str:
        """Build an IN or NOT IN clause."""
        if not values:
            # Empty list: IN () is always false, NOT IN () is always true
            return "1 = 0" if not negated else "1 = 1"
        placeholders = [self._add_param(v) for v in values]
        op = "NOT IN" if negated else "IN"
        return f"{column} {op} ({', '.join(placeholders)})"

    def _build_between(self, column: str, min_val: Any, max_val: Any) -> str:
        """Build a BETWEEN clause."""
        p1 = self._add_param(min_val)
        p2 = self._add_param(max_val)
        return f"{column} BETWEEN {p1} AND {p2}"

    def _apply_policy_with(
        self,
        sql: str,
        args: tuple[Any, ...],
        enforcer_method: str,
    ) -> tuple[str, tuple[Any, ...]]:
        """Apply access policy using the named enforcer method.

        Args:
            sql: SQL query string.
            args: Query arguments.
            enforcer_method: Method name on the policy enforcer to call
                (e.g. "apply_to_select", "apply_to_update", "apply_to_delete").

        Returns:
            Tuple of (sql, args) with policy applied, or original (sql, args) if no policy.
        """
        result = self._should_apply_policy()
        if result is None:
            return sql, args
        enforcer, policy, context = result
        return getattr(enforcer, enforcer_method)(
            sql, args, self._table, policy, context
        )

    async def fetch_one(self) -> "Row | None":
        """Execute query and fetch one row.

        Subclasses that support RETURNING or SELECT should override this method.
        """
        raise NotImplementedError(f"{type(self).__name__} does not support fetch_one()")

    async def fetch_val(self) -> Any:
        """Execute query and fetch the first column of the first row."""
        row = await self.fetch_one()
        if row is None:
            return None
        values = list(row.values())
        return values[0] if values else None
