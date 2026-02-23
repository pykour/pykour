"""DELETE query builder."""

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
        self._where_clauses: list[str] = []
        self._returning: list[str] = []

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
        return self._apply_policy_with(sql, args, "apply_to_delete")

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
