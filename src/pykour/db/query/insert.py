"""INSERT query builder."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Self

from pykour.db.access_policy.resolver import ValueResolver
from pykour.db.query.base import (
    BaseQuery,
    ExecuteFunc,
    FetchAllFunc,
    FetchOneFunc,
    GetPolicyContextFunc,
)

if TYPE_CHECKING:
    from pykour.db.access_policy.enforcer import BasePolicyEnforcer
    from pykour.db.access_policy.policy import AccessPolicy
    from pykour.db.result import Row


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
        self._values_data: list[dict[str, Any]] = []
        self._returning: list[str] = []
        self._on_conflict: str | None = None

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

    def _apply_column_auto_set(
        self, values_data: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply column-level auto_set values for INSERT.

        Args:
            values_data: List of row data dictionaries.

        Returns:
            Modified values_data with auto-set values applied.
        """
        table_class = self._table_classes.get(self._table)
        if table_class is None:
            return values_data

        # Get columns with auto-set options for INSERT
        get_auto_set_columns = getattr(table_class, "get_auto_set_columns", None)
        if get_auto_set_columns is None:
            return values_data

        auto_set_columns = get_auto_set_columns(on_insert=True)
        if not auto_set_columns:
            return values_data

        # Get context for value resolution
        context = None
        if self._get_policy_context is not None:
            context = self._get_policy_context()
            if context is not None and context.bypass_enforcement:
                context = None

        resolver = ValueResolver(context)

        # Apply auto-set values to each row
        modified_values = []
        for row in values_data:
            new_row = row.copy()
            for col_name, col in auto_set_columns.items():
                # Skip if user already provided a value
                if col_name in new_row:
                    continue

                value = resolver.resolve_for_insert(
                    col.auto_now_add,
                    col.auto_now,
                    col.auto_set_on_insert,
                    col.auto_set,
                )
                if value is not None:
                    new_row[col_name] = value
            modified_values.append(new_row)

        return modified_values

    def _apply_policy(self) -> list[dict[str, Any]]:
        """Apply access policy and column auto_set to INSERT data."""
        # First apply column-level auto_set
        values_data = self._apply_column_auto_set(self._values_data)

        # Then apply access policy auto_set
        result = self._should_apply_policy()
        if result is None:
            return values_data

        enforcer, policy, context = result
        # Apply policy to get modified values
        _, _, modified_values = enforcer.apply_to_insert(
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
