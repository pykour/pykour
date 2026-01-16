"""Query builder factory for Pykour database."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine

from pykour.db.query import DeleteQuery, InsertQuery, SelectQuery, UpdateQuery
from pykour.db.result import Row

if TYPE_CHECKING:
    from pykour.db.connection import ConnectionManager
    from pykour.db.policy_manager import AccessPolicyManager

# Type aliases for query executor callbacks
ExecuteCallback = Callable[[str, tuple[Any, ...]], Coroutine[Any, Any, int]]
FetchAllCallback = Callable[[str, tuple[Any, ...]], Coroutine[Any, Any, list[Row]]]
FetchOneCallback = Callable[[str, tuple[Any, ...]], Coroutine[Any, Any, Row | None]]


class QueryBuilderFactory:
    """Factory for creating query builders.

    This class creates SELECT, INSERT, UPDATE, and DELETE query builders
    with proper callbacks for query execution.

    Example:
        factory = QueryBuilderFactory(conn_manager, policy_manager)

        # Create a SELECT query
        query = factory.select("id", "name").from_("users")
        users = await query.fetch_all()

        # Create an INSERT query
        query = factory.insert("users").values(name="Alice")
        await query.execute()
    """

    def __init__(
        self,
        connection_manager: "ConnectionManager",
        policy_manager: "AccessPolicyManager",
    ) -> None:
        """Initialize the query builder factory.

        Args:
            connection_manager: Connection manager for database operations.
            policy_manager: Access policy manager for row-level security.
        """
        self._conn = connection_manager
        self._policy = policy_manager

    async def _execute_for_query(self, sql: str, args: tuple[Any, ...]) -> int:
        """Execute a query and return affected rows.

        Auto-commits if not in a transaction.

        Args:
            sql: SQL query with $N placeholders.
            args: Query arguments.

        Returns:
            Number of affected rows.
        """
        conn = await self._conn.acquire()
        try:
            converted_sql = self._conn.convert_placeholders(sql, len(args))
            result = await self._conn.execute(conn, converted_sql, args)
            # Auto-commit if not in a transaction
            if self._conn.transaction_connection is None:
                await self._conn.commit(conn)
            return result
        finally:
            await self._conn.release(conn)

    async def _fetch_all_for_query(self, sql: str, args: tuple[Any, ...]) -> list[Row]:
        """Fetch all rows from a query.

        Args:
            sql: SQL query with $N placeholders.
            args: Query arguments.

        Returns:
            List of Row objects.
        """
        conn = await self._conn.acquire()
        try:
            converted_sql = self._conn.convert_placeholders(sql, len(args))
            return await self._conn.fetch_all(conn, converted_sql, args)
        finally:
            await self._conn.release(conn)

    async def _fetch_one_for_query(self, sql: str, args: tuple[Any, ...]) -> Row | None:
        """Fetch one row from a query.

        Args:
            sql: SQL query with $N placeholders.
            args: Query arguments.

        Returns:
            Row or None.
        """
        conn = await self._conn.acquire()
        try:
            converted_sql = self._conn.convert_placeholders(sql, len(args))
            return await self._conn.fetch_one(conn, converted_sql, args)
        finally:
            await self._conn.release(conn)

    def select(self, *columns: str) -> SelectQuery:
        """Create a SELECT query builder.

        Args:
            *columns: Columns to select. Use "*" for all columns.

        Returns:
            SelectQuery builder instance.
        """
        self._conn.check_connected()
        return SelectQuery(
            columns,
            self._execute_for_query,
            self._fetch_all_for_query,
            self._fetch_one_for_query,
            **self._policy.get_policy_kwargs(),
        )

    def insert(self, table: str) -> InsertQuery:
        """Create an INSERT query builder.

        Args:
            table: Table to insert into.

        Returns:
            InsertQuery builder instance.
        """
        self._conn.check_connected()
        return InsertQuery(
            table,
            self._execute_for_query,
            self._fetch_all_for_query,
            self._fetch_one_for_query,
            **self._policy.get_policy_kwargs(),
        )

    def update(self, table: str) -> UpdateQuery:
        """Create an UPDATE query builder.

        Args:
            table: Table to update.

        Returns:
            UpdateQuery builder instance.
        """
        self._conn.check_connected()
        return UpdateQuery(
            table,
            self._execute_for_query,
            self._fetch_all_for_query,
            self._fetch_one_for_query,
            **self._policy.get_policy_kwargs(),
        )

    def delete(self, table: str) -> DeleteQuery:
        """Create a DELETE query builder.

        Args:
            table: Table to delete from.

        Returns:
            DeleteQuery builder instance.
        """
        self._conn.check_connected()
        return DeleteQuery(
            table,
            self._execute_for_query,
            self._fetch_all_for_query,
            self._fetch_one_for_query,
            **self._policy.get_policy_kwargs(),
        )
