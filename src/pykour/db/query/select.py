"""SELECT query builder."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

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
