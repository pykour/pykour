"""UPDATE query builder."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from pykour.db.access_policy.resolver import ValueResolver
from pykour.db.query.base import (
    BaseQuery,
    ExecuteFunc,
    FetchAllFunc,
    FetchOneFunc,
    GetPolicyContextFunc,
)
from pykour.db.query.where import WhereClauseMixin

if TYPE_CHECKING:
    from pykour.db.access_policy.enforcer import BasePolicyEnforcer
    from pykour.db.access_policy.policy import AccessPolicy
    from pykour.db.result import Row


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
        table_classes: dict[str, type] | None = None,
        get_policy_context: GetPolicyContextFunc | None = None,
    ) -> None:
        super().__init__(
            execute_func,
            fetch_all_func,
            fetch_one_func,
            policy_enforcer=policy_enforcer,
            table_policies=table_policies,
            table_classes=table_classes,
            get_policy_context=get_policy_context,
        )
        self._table = table
        self._set_clauses: list[str] = []
        self._set_data: dict[str, Any] = {}  # Track user-provided set data
        self._where_clauses: list[str] = []
        self._returning: list[str] = []

    def set(self, **data: Any) -> Self:
        """Set columns to update.

        Args:
            **data: Column-value pairs.
        """
        for key, value in data.items():
            self._set_data[key] = value
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

    def _apply_column_auto_set(self) -> list[str]:
        """Apply column-level auto_set values for UPDATE.

        Returns:
            Additional SET clauses for auto-set columns.
        """
        table_class = self._table_classes.get(self._table)
        if table_class is None:
            return []

        # Get columns with auto-set options for UPDATE
        get_auto_set_columns = getattr(table_class, "get_auto_set_columns", None)
        if get_auto_set_columns is None:
            return []

        auto_set_columns = get_auto_set_columns(on_insert=False)
        if not auto_set_columns:
            return []

        # Get context for value resolution
        context = None
        if self._get_policy_context is not None:
            context = self._get_policy_context()
            if context is not None and context.bypass_enforcement:
                context = None

        resolver = ValueResolver(context)

        # Build additional SET clauses
        additional_clauses = []
        for col_name, col in auto_set_columns.items():
            # Skip if user already provided a value for this column
            if col_name in self._set_data:
                continue

            value = resolver.resolve_for_update(col.auto_now, col.auto_set)
            if value is not None:
                placeholder = self._add_param(value)
                additional_clauses.append(f"{col_name} = {placeholder}")

        return additional_clauses

    def _build_sql(self) -> str:
        """Build the SQL query string."""
        # Apply column-level auto_set and get additional clauses
        auto_set_clauses = self._apply_column_auto_set()
        all_clauses = self._set_clauses + auto_set_clauses

        if not all_clauses:
            raise ValueError("No columns specified for UPDATE")

        sql = f"UPDATE {self._table} SET {', '.join(all_clauses)}"

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
