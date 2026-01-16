"""Query builder classes."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Coroutine, Self

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

    # These are set by subclasses that support access policies
    _policy_enforcer: "BasePolicyEnforcer | None"
    _table_policies: dict[str, "AccessPolicy"]
    _get_policy_context: GetPolicyContextFunc | None
    _table: str

    def __init__(
        self,
        execute_func: ExecuteFunc,
        fetch_all_func: FetchAllFunc,
        fetch_one_func: FetchOneFunc,
    ) -> None:
        self._execute_func = execute_func
        self._fetch_all_func = fetch_all_func
        self._fetch_one_func = fetch_one_func
        self._params: list[Any] = []

    def _should_apply_policy(self) -> "tuple[AccessPolicy, PolicyContextData] | None":
        """Check if policy should be applied and return policy and context.

        Returns:
            Tuple of (policy, context) if policy should be applied, None otherwise.
        """
        if (
            not hasattr(self, "_policy_enforcer")
            or self._policy_enforcer is None
            or not hasattr(self, "_get_policy_context")
            or self._get_policy_context is None
        ):
            return None

        context = self._get_policy_context()
        if context is None or context.bypass_enforcement:
            return None

        if not hasattr(self, "_table_policies"):
            return None

        policy = self._table_policies.get(self._table)
        if policy is None:
            return None

        return policy, context

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


class WhereClauseMixin:
    """Mixin providing comparison operator methods for queries with WHERE clauses."""

    _where_clauses: list[str]
    _add_param: Callable[[Any], str]
    _build_comparison: Callable[[str, str, Any], str]
    _build_in_clause: Callable[[str, list[Any], bool], str]
    _build_between: Callable[[str, Any, Any], str]

    def where_gt(self, column: str, value: Any) -> Self:
        """Add WHERE column > value condition.

        Args:
            column: Column name.
            value: Value to compare against.
        """
        self._where_clauses.append(self._build_comparison(column, ">", value))
        return self

    def where_gte(self, column: str, value: Any) -> Self:
        """Add WHERE column >= value condition.

        Args:
            column: Column name.
            value: Value to compare against.
        """
        self._where_clauses.append(self._build_comparison(column, ">=", value))
        return self

    def where_lt(self, column: str, value: Any) -> Self:
        """Add WHERE column < value condition.

        Args:
            column: Column name.
            value: Value to compare against.
        """
        self._where_clauses.append(self._build_comparison(column, "<", value))
        return self

    def where_lte(self, column: str, value: Any) -> Self:
        """Add WHERE column <= value condition.

        Args:
            column: Column name.
            value: Value to compare against.
        """
        self._where_clauses.append(self._build_comparison(column, "<=", value))
        return self

    def where_in(self, column: str, values: list[Any]) -> Self:
        """Add WHERE column IN (...) condition.

        Args:
            column: Column name.
            values: List of values.
        """
        self._where_clauses.append(self._build_in_clause(column, values, False))
        return self

    def where_not_in(self, column: str, values: list[Any]) -> Self:
        """Add WHERE column NOT IN (...) condition.

        Args:
            column: Column name.
            values: List of values.
        """
        self._where_clauses.append(self._build_in_clause(column, values, True))
        return self

    def where_between(self, column: str, min_val: Any, max_val: Any) -> Self:
        """Add WHERE column BETWEEN min AND max condition.

        Args:
            column: Column name.
            min_val: Minimum value (inclusive).
            max_val: Maximum value (inclusive).
        """
        self._where_clauses.append(self._build_between(column, min_val, max_val))
        return self

    def where_like(self, column: str, pattern: str) -> Self:
        """Add WHERE column LIKE pattern condition.

        Args:
            column: Column name.
            pattern: SQL LIKE pattern (use % for wildcards).
        """
        self._where_clauses.append(self._build_comparison(column, "LIKE", pattern))
        return self

    def where_is_null(self, column: str) -> Self:
        """Add WHERE column IS NULL condition.

        Args:
            column: Column name.
        """
        self._where_clauses.append(f"{column} IS NULL")
        return self

    def where_is_not_null(self, column: str) -> Self:
        """Add WHERE column IS NOT NULL condition.

        Args:
            column: Column name.
        """
        self._where_clauses.append(f"{column} IS NOT NULL")
        return self


class SelectQuery(WhereClauseMixin, BaseQuery):
    """SELECT query builder.

    Example:
        query = db.select("id", "name").from_("users").where(active=True)
        users = await query.fetch_all()
    """

    def __init__(
        self,
        columns: tuple[str, ...],
        execute_func: ExecuteFunc,
        fetch_all_func: FetchAllFunc,
        fetch_one_func: FetchOneFunc,
        *,
        policy_enforcer: "BasePolicyEnforcer | None" = None,
        table_policies: dict[str, "AccessPolicy"] | None = None,
        get_policy_context: GetPolicyContextFunc | None = None,
    ) -> None:
        super().__init__(execute_func, fetch_all_func, fetch_one_func)
        self._columns = columns or ("*",)
        self._table: str = ""
        self._where_clauses: list[str] = []
        self._order_by: list[str] = []
        self._limit_value: int | None = None
        self._offset_value: int | None = None
        self._joins: list[str] = []
        self._group_by: list[str] = []
        self._having_clauses: list[str] = []
        self._distinct: bool = False
        # Policy support
        self._policy_enforcer = policy_enforcer
        self._table_policies = table_policies or {}
        self._get_policy_context = get_policy_context

    def distinct(self) -> Self:
        """Enable SELECT DISTINCT."""
        self._distinct = True
        return self

    def from_(self, table: str) -> Self:
        """Set the table to select from."""
        self._table = table
        return self

    def where(self, **conditions: Any) -> Self:
        """Add WHERE conditions (AND).

        Args:
            **conditions: Column-value pairs for equality conditions.
        """
        self._where_clauses = self._build_where_clause(conditions, self._where_clauses)
        return self

    def where_raw(self, condition: str, *args: Any) -> Self:
        """Add a raw WHERE condition.

        Args:
            condition: SQL condition with $1, $2, ... placeholders.
            *args: Values for the placeholders.
        """
        processed = self._process_raw_condition(condition, args)
        self._where_clauses.append(processed)
        return self

    def order_by(self, *columns: str, desc: bool = False) -> Self:
        """Add ORDER BY clause.

        Args:
            *columns: Columns to order by.
            desc: If True, order descending.
        """
        direction = "DESC" if desc else "ASC"
        for col in columns:
            self._order_by.append(f"{col} {direction}")
        return self

    def limit(self, n: int) -> Self:
        """Set LIMIT clause."""
        self._limit_value = n
        return self

    def offset(self, n: int) -> Self:
        """Set OFFSET clause."""
        self._offset_value = n
        return self

    def join(self, table: str, on: str) -> Self:
        """Add INNER JOIN clause."""
        self._joins.append(f"INNER JOIN {table} ON {on}")
        return self

    def left_join(self, table: str, on: str) -> Self:
        """Add LEFT JOIN clause."""
        self._joins.append(f"LEFT JOIN {table} ON {on}")
        return self

    def group_by(self, *columns: str) -> Self:
        """Add GROUP BY clause."""
        self._group_by.extend(columns)
        return self

    def having(self, condition: str, *args: Any) -> Self:
        """Add HAVING clause.

        Args:
            condition: SQL condition with $1, $2, ... placeholders.
            *args: Values for the placeholders.
        """
        processed = self._process_raw_condition(condition, args)
        self._having_clauses.append(processed)
        return self

    def _build_sql(self) -> str:
        """Build the SQL query string."""
        distinct_keyword = "DISTINCT " if self._distinct else ""
        parts = [f"SELECT {distinct_keyword}{', '.join(self._columns)}"]

        if self._table:
            parts.append(f"FROM {self._table}")

        for join in self._joins:
            parts.append(join)

        if self._where_clauses:
            parts.append(f"WHERE {' AND '.join(self._where_clauses)}")

        if self._group_by:
            parts.append(f"GROUP BY {', '.join(self._group_by)}")

        if self._having_clauses:
            parts.append(f"HAVING {' AND '.join(self._having_clauses)}")

        if self._order_by:
            parts.append(f"ORDER BY {', '.join(self._order_by)}")

        if self._limit_value is not None:
            parts.append(f"LIMIT {self._limit_value}")

        if self._offset_value is not None:
            parts.append(f"OFFSET {self._offset_value}")

        return " ".join(parts)

    def _apply_policy(
        self, sql: str, args: tuple[Any, ...]
    ) -> tuple[str, tuple[Any, ...]]:
        """Apply access policy to the query."""
        result = self._should_apply_policy()
        if result is None:
            return sql, args
        policy, context = result
        # _should_apply_policy already verified _policy_enforcer is not None
        assert self._policy_enforcer is not None
        return self._policy_enforcer.apply_to_select(
            sql, args, self._table, policy, context
        )

    async def fetch_all(self) -> list["Row"]:
        """Execute query and fetch all rows."""
        sql = self._build_sql()
        sql, args = self._apply_policy(sql, tuple(self._params))
        return await self._fetch_all_func(sql, args)

    async def fetch_one(self) -> "Row | None":
        """Execute query and fetch one row."""
        sql = self._build_sql()
        sql, args = self._apply_policy(sql, tuple(self._params))
        return await self._fetch_one_func(sql, args)

    async def fetch_val(self) -> Any:
        """Execute query and fetch the first column of the first row."""
        row = await self.fetch_one()
        if row is None:
            return None
        # Get first value from the row
        values = list(row.values())
        return values[0] if values else None


class InsertQuery(BaseQuery):
    """INSERT query builder.

    Example:
        await db.insert("users").values(name="Alice", age=30).execute()
    """

    def __init__(
        self,
        table: str,
        execute_func: ExecuteFunc,
        fetch_all_func: FetchAllFunc,
        fetch_one_func: FetchOneFunc,
        *,
        policy_enforcer: "BasePolicyEnforcer | None" = None,
        table_policies: dict[str, "AccessPolicy"] | None = None,
        get_policy_context: GetPolicyContextFunc | None = None,
    ) -> None:
        super().__init__(execute_func, fetch_all_func, fetch_one_func)
        self._table = table
        self._values_data: list[dict[str, Any]] = []
        self._returning: list[str] = []
        self._on_conflict: str | None = None
        # Policy support
        self._policy_enforcer = policy_enforcer
        self._table_policies = table_policies or {}
        self._get_policy_context = get_policy_context

    def values(self, **data: Any) -> Self:
        """Set values to insert.

        Args:
            **data: Column-value pairs.
        """
        self._values_data.append(data)
        return self

    def values_many(self, rows: list[dict[str, Any]]) -> Self:
        """Set multiple rows to insert.

        Args:
            rows: List of column-value dicts.
        """
        self._values_data.extend(rows)
        return self

    def returning(self, *columns: str) -> Self:
        """Add RETURNING clause."""
        self._returning.extend(columns)
        return self

    def on_conflict_do_nothing(
        self,
        conflict_target: str | Sequence[str] | None = None,
        *,
        constraint: str | None = None,
    ) -> Self:
        """Add ON CONFLICT DO NOTHING clause.

        Args:
            conflict_target: Column(s) that define the conflict target.
                Can be a single column name or sequence of column names.
            constraint: Name of a unique constraint to use as conflict target.
                Mutually exclusive with conflict_target.

        Raises:
            ValueError: If both conflict_target and constraint are provided.
        """
        target_clause = self._build_conflict_target(conflict_target, constraint)
        self._on_conflict = f"{target_clause}DO NOTHING"
        return self

    def on_conflict_do_update(
        self,
        conflict_target: str | Sequence[str] | None = None,
        *,
        constraint: str | None = None,
        **data: Any,
    ) -> Self:
        """Add ON CONFLICT DO UPDATE clause.

        Args:
            conflict_target: Column(s) that define the conflict target.
                Can be a single column name or sequence of column names.
            constraint: Name of a unique constraint to use as conflict target.
                Mutually exclusive with conflict_target.
            **data: Column-value pairs to update on conflict.

        Raises:
            ValueError: If both conflict_target and constraint are provided,
                or if no data is provided for update.
        """
        if not data:
            raise ValueError("No columns specified for ON CONFLICT DO UPDATE")

        target_clause = self._build_conflict_target(conflict_target, constraint)
        updates = []
        for key, value in data.items():
            placeholder = self._add_param(value)
            updates.append(f"{key} = {placeholder}")
        self._on_conflict = f"{target_clause}DO UPDATE SET {', '.join(updates)}"
        return self

    def _build_conflict_target(
        self,
        conflict_target: str | Sequence[str] | None,
        constraint: str | None,
    ) -> str:
        """Build the conflict target clause for ON CONFLICT.

        Args:
            conflict_target: Column(s) for conflict detection.
            constraint: Constraint name for conflict detection.

        Returns:
            Formatted conflict target clause (with trailing space) or empty string.

        Raises:
            ValueError: If both conflict_target and constraint are provided.
        """
        if conflict_target is not None and constraint is not None:
            raise ValueError(
                "Cannot specify both 'conflict_target' and 'constraint'; "
                "use one or the other"
            )

        if constraint is not None:
            return f"ON CONSTRAINT {constraint} "

        if conflict_target is not None:
            if isinstance(conflict_target, str):
                columns = conflict_target
            else:
                columns = ", ".join(conflict_target)
            return f"({columns}) "

        return ""

    def _apply_policy(self) -> list[dict[str, Any]]:
        """Apply access policy to INSERT data (auto_set)."""
        values_data = self._values_data

        if self._policy_enforcer is None or self._get_policy_context is None:
            return values_data

        context = self._get_policy_context()
        if context is None or context.bypass_enforcement:
            return values_data

        policy = self._table_policies.get(self._table)
        if policy is None:
            return values_data

        # Apply policy to get modified values
        _, _, modified_values = self._policy_enforcer.apply_to_insert(
            "",  # SQL not used here
            (),  # args not used here
            self._table,
            policy,
            context,
            values_data,
        )
        return modified_values

    def _build_sql(self, values_data: list[dict[str, Any]] | None = None) -> str:
        """Build the SQL query string."""
        if values_data is None:
            values_data = self._values_data
        if not values_data:
            raise ValueError("No values specified for INSERT")

        # Reset params for rebuild
        self._params = []

        # Get columns from first row
        columns = list(values_data[0].keys())
        col_str = ", ".join(columns)

        # Build VALUES clause
        values_parts = []
        for row in values_data:
            placeholders = []
            for col in columns:
                value = row.get(col)
                placeholders.append(self._add_param(value))
            values_parts.append(f"({', '.join(placeholders)})")

        sql = f"INSERT INTO {self._table} ({col_str}) VALUES {', '.join(values_parts)}"

        if self._on_conflict:
            sql += f" ON CONFLICT {self._on_conflict}"

        if self._returning:
            sql += f" RETURNING {', '.join(self._returning)}"

        return sql

    async def execute(self) -> int:
        """Execute the insert and return affected rows."""
        values_data = self._apply_policy()
        sql = self._build_sql(values_data)
        return await self._execute_func(sql, tuple(self._params))

    async def fetch_one(self) -> "Row | None":
        """Execute and fetch the returned row."""
        values_data = self._apply_policy()
        sql = self._build_sql(values_data)
        return await self._fetch_one_func(sql, tuple(self._params))

    async def fetch_val(self) -> Any:
        """Execute and fetch the first column of the returned row."""
        row = await self.fetch_one()
        if row is None:
            return None
        values = list(row.values())
        return values[0] if values else None


class UpdateQuery(WhereClauseMixin, BaseQuery):
    """UPDATE query builder.

    Example:
        await db.update("users").set(name="Bob").where(id=1).execute()
    """

    def __init__(
        self,
        table: str,
        execute_func: ExecuteFunc,
        fetch_all_func: FetchAllFunc,
        fetch_one_func: FetchOneFunc,
        *,
        policy_enforcer: "BasePolicyEnforcer | None" = None,
        table_policies: dict[str, "AccessPolicy"] | None = None,
        get_policy_context: GetPolicyContextFunc | None = None,
    ) -> None:
        super().__init__(execute_func, fetch_all_func, fetch_one_func)
        self._table = table
        self._set_clauses: list[str] = []
        self._where_clauses: list[str] = []
        self._returning: list[str] = []
        # Policy support
        self._policy_enforcer = policy_enforcer
        self._table_policies = table_policies or {}
        self._get_policy_context = get_policy_context

    def set(self, **data: Any) -> Self:
        """Set columns to update.

        Args:
            **data: Column-value pairs.
        """
        for key, value in data.items():
            placeholder = self._add_param(value)
            self._set_clauses.append(f"{key} = {placeholder}")
        return self

    def where(self, **conditions: Any) -> Self:
        """Add WHERE conditions (AND)."""
        self._where_clauses = self._build_where_clause(conditions, self._where_clauses)
        return self

    def where_raw(self, condition: str, *args: Any) -> Self:
        """Add a raw WHERE condition."""
        processed = self._process_raw_condition(condition, args)
        self._where_clauses.append(processed)
        return self

    def returning(self, *columns: str) -> Self:
        """Add RETURNING clause."""
        self._returning.extend(columns)
        return self

    def _build_sql(self) -> str:
        """Build the SQL query string."""
        if not self._set_clauses:
            raise ValueError("No columns specified for UPDATE")

        sql = f"UPDATE {self._table} SET {', '.join(self._set_clauses)}"

        if self._where_clauses:
            sql += f" WHERE {' AND '.join(self._where_clauses)}"

        if self._returning:
            sql += f" RETURNING {', '.join(self._returning)}"

        return sql

    def _apply_policy(
        self, sql: str, args: tuple[Any, ...]
    ) -> tuple[str, tuple[Any, ...]]:
        """Apply access policy to the query."""
        result = self._should_apply_policy()
        if result is None:
            return sql, args
        policy, context = result
        # _should_apply_policy already verified _policy_enforcer is not None
        assert self._policy_enforcer is not None
        return self._policy_enforcer.apply_to_update(
            sql, args, self._table, policy, context
        )

    async def execute(self) -> int:
        """Execute the update and return affected rows."""
        sql = self._build_sql()
        sql, args = self._apply_policy(sql, tuple(self._params))
        return await self._execute_func(sql, args)

    async def fetch_all(self) -> list["Row"]:
        """Execute and fetch all returned rows."""
        sql = self._build_sql()
        sql, args = self._apply_policy(sql, tuple(self._params))
        return await self._fetch_all_func(sql, args)


class DeleteQuery(WhereClauseMixin, BaseQuery):
    """DELETE query builder.

    Example:
        await db.delete("users").where(id=1).execute()
    """

    def __init__(
        self,
        table: str,
        execute_func: ExecuteFunc,
        fetch_all_func: FetchAllFunc,
        fetch_one_func: FetchOneFunc,
        *,
        policy_enforcer: "BasePolicyEnforcer | None" = None,
        table_policies: dict[str, "AccessPolicy"] | None = None,
        get_policy_context: GetPolicyContextFunc | None = None,
    ) -> None:
        super().__init__(execute_func, fetch_all_func, fetch_one_func)
        self._table = table
        self._where_clauses: list[str] = []
        self._returning: list[str] = []
        # Policy support
        self._policy_enforcer = policy_enforcer
        self._table_policies = table_policies or {}
        self._get_policy_context = get_policy_context

    def where(self, **conditions: Any) -> Self:
        """Add WHERE conditions (AND)."""
        self._where_clauses = self._build_where_clause(conditions, self._where_clauses)
        return self

    def where_raw(self, condition: str, *args: Any) -> Self:
        """Add a raw WHERE condition."""
        processed = self._process_raw_condition(condition, args)
        self._where_clauses.append(processed)
        return self

    def returning(self, *columns: str) -> Self:
        """Add RETURNING clause."""
        self._returning.extend(columns)
        return self

    def _build_sql(self) -> str:
        """Build the SQL query string."""
        sql = f"DELETE FROM {self._table}"

        if self._where_clauses:
            sql += f" WHERE {' AND '.join(self._where_clauses)}"

        if self._returning:
            sql += f" RETURNING {', '.join(self._returning)}"

        return sql

    def _apply_policy(
        self, sql: str, args: tuple[Any, ...]
    ) -> tuple[str, tuple[Any, ...]]:
        """Apply access policy to the query."""
        result = self._should_apply_policy()
        if result is None:
            return sql, args
        policy, context = result
        # _should_apply_policy already verified _policy_enforcer is not None
        assert self._policy_enforcer is not None
        return self._policy_enforcer.apply_to_delete(
            sql, args, self._table, policy, context
        )

    async def execute(self) -> int:
        """Execute the delete and return affected rows."""
        sql = self._build_sql()
        sql, args = self._apply_policy(sql, tuple(self._params))
        return await self._execute_func(sql, args)

    async def fetch_all(self) -> list["Row"]:
        """Execute and fetch all returned rows."""
        sql = self._build_sql()
        sql, args = self._apply_policy(sql, tuple(self._params))
        return await self._fetch_all_func(sql, args)
