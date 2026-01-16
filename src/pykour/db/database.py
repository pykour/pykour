"""Main Database class."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pykour.db.connection import ConnectionManager
from pykour.db.policy_manager import AccessPolicyManager
from pykour.db.query import DeleteQuery, InsertQuery, SelectQuery, UpdateQuery
from pykour.db.query_factory import QueryBuilderFactory
from pykour.db.result import Row
from pykour.db.transaction import Transaction

if TYPE_CHECKING:
    from pykour.db.access_policy.policy import AccessPolicy


class Database:
    """Database connection manager and query builder factory.

    Example:
        db = Database("sqlite:///app.db")
        await db.connect()

        # Query builder API
        users = await db.select("*").from_("users").where(active=True).fetch_all()

        # Raw SQL
        users = await db.fetch_all("SELECT * FROM users WHERE active = $1", True)

        # Transaction
        async with db.transaction():
            await db.insert("users").values(name="Alice").execute()

        await db.disconnect()

    AccessPolicy Example:
        from pykour.db.access_policy import AccessPolicy, set_policy_context

        # Define table with policy
        class OrderTable(Table):
            __tablename__ = "orders"
            __access_policy__ = AccessPolicy(
                select=["tenant_id = :tenant_id"],
                auto_set={"tenant_id": ":tenant_id"},
            )

        # Register table and set context
        db.register_table(OrderTable)
        set_policy_context(tenant_id="tenant-123")

        # Queries automatically filtered by policy
        orders = await db.select("*").from_("orders").fetch_all()
    """

    def __init__(
        self,
        url: str,
        min_size: int = 1,
        max_size: int = 10,
        *,
        enable_access_policies: bool = True,
    ) -> None:
        """Initialize database connection.

        Args:
            url: Database connection URL.
                - SQLite: sqlite:///path/to/db.sqlite or sqlite:///:memory:
                - PostgreSQL: postgresql://user:pass@host:port/dbname
                - MySQL: mysql://user:pass@host:port/dbname
            min_size: Minimum number of connections in the pool.
            max_size: Maximum number of connections in the pool.
            enable_access_policies: Enable access policy enforcement.
        """
        self._conn_manager = ConnectionManager(url, min_size, max_size)
        self._policy_manager = AccessPolicyManager(enable_access_policies)
        self._query_factory: QueryBuilderFactory | None = None

    @property
    def driver_name(self) -> str:
        """Get the database driver name."""
        return self._conn_manager.driver_name

    @property
    def _driver(self) -> Any:
        """Get the database driver (internal use only).

        Used by migration runner and other internal modules.
        """
        return self._conn_manager.driver

    async def connect(self) -> None:
        """Connect to the database."""
        await self._conn_manager.connect()

        # Initialize policy enforcer after connection
        self._policy_manager.initialize_enforcer(self._conn_manager.driver_name)

        # Create query factory
        self._query_factory = QueryBuilderFactory(
            self._conn_manager,
            self._policy_manager,
        )

    async def disconnect(self) -> None:
        """Disconnect from the database."""
        await self._conn_manager.disconnect()

    # Access Policy methods (delegated to AccessPolicyManager)

    def register_table(self, table_class: type) -> None:
        """Register a table class and its access policy.

        Args:
            table_class: A Table subclass with optional __access_policy__.
        """
        self._policy_manager.register_table(table_class)

    def register_policy(self, table_name: str, policy: "AccessPolicy") -> None:
        """Register an access policy for a table.

        Args:
            table_name: Name of the table.
            policy: AccessPolicy instance.
        """
        self._policy_manager.register_policy(table_name, policy)

    def get_policy(self, table_name: str) -> "AccessPolicy | None":
        """Get the access policy for a table.

        Args:
            table_name: Name of the table.

        Returns:
            AccessPolicy or None if not registered.
        """
        return self._policy_manager.get_policy(table_name)

    # Raw SQL methods

    async def execute(self, sql: str, *args: Any) -> int:
        """Execute a query without returning results.

        Args:
            sql: SQL query with $1, $2, ... placeholders.
            *args: Query parameters.

        Returns:
            Number of affected rows.
        """
        self._conn_manager.check_connected()
        conn = await self._conn_manager.acquire()
        try:
            converted_sql = self._conn_manager.convert_placeholders(sql, len(args))
            result = await self._conn_manager.execute(conn, converted_sql, args)
            # Auto-commit if not in a transaction
            if self._conn_manager.transaction_connection is None:
                await self._conn_manager.commit(conn)
            return result
        finally:
            await self._conn_manager.release(conn)

    async def fetch_all(self, sql: str, *args: Any) -> list[Row]:
        """Fetch all rows from a query.

        Args:
            sql: SQL query with $1, $2, ... placeholders.
            *args: Query parameters.

        Returns:
            List of Row objects.
        """
        self._conn_manager.check_connected()
        conn = await self._conn_manager.acquire()
        try:
            converted_sql = self._conn_manager.convert_placeholders(sql, len(args))
            return await self._conn_manager.fetch_all(conn, converted_sql, args)
        finally:
            await self._conn_manager.release(conn)

    async def fetch_one(self, sql: str, *args: Any) -> Row | None:
        """Fetch a single row from a query.

        Args:
            sql: SQL query with $1, $2, ... placeholders.
            *args: Query parameters.

        Returns:
            A Row object or None if no results.
        """
        self._conn_manager.check_connected()
        conn = await self._conn_manager.acquire()
        try:
            converted_sql = self._conn_manager.convert_placeholders(sql, len(args))
            return await self._conn_manager.fetch_one(conn, converted_sql, args)
        finally:
            await self._conn_manager.release(conn)

    async def fetch_val(self, sql: str, *args: Any) -> Any:
        """Fetch the first column of the first row.

        Args:
            sql: SQL query with $1, $2, ... placeholders.
            *args: Query parameters.

        Returns:
            The first column value or None.
        """
        row = await self.fetch_one(sql, *args)
        if row is None:
            return None
        values = list(row.values())
        return values[0] if values else None

    # Query builder methods (delegated to QueryBuilderFactory)

    def select(self, *columns: str) -> SelectQuery:
        """Create a SELECT query builder.

        Args:
            *columns: Columns to select. Use "*" for all columns.

        Returns:
            SelectQuery builder instance.
        """
        if self._query_factory is None:
            self._conn_manager.check_connected()
        return self._query_factory.select(*columns)  # type: ignore[union-attr]

    def insert(self, table: str) -> InsertQuery:
        """Create an INSERT query builder.

        Args:
            table: Table to insert into.

        Returns:
            InsertQuery builder instance.
        """
        if self._query_factory is None:
            self._conn_manager.check_connected()
        return self._query_factory.insert(table)  # type: ignore[union-attr]

    def update(self, table: str) -> UpdateQuery:
        """Create an UPDATE query builder.

        Args:
            table: Table to update.

        Returns:
            UpdateQuery builder instance.
        """
        if self._query_factory is None:
            self._conn_manager.check_connected()
        return self._query_factory.update(table)  # type: ignore[union-attr]

    def delete(self, table: str) -> DeleteQuery:
        """Create a DELETE query builder.

        Args:
            table: Table to delete from.

        Returns:
            DeleteQuery builder instance.
        """
        if self._query_factory is None:
            self._conn_manager.check_connected()
        return self._query_factory.delete(table)  # type: ignore[union-attr]

    # Transaction

    async def transaction(self) -> Transaction:
        """Create a transaction context manager.

        Example:
            async with await db.transaction():
                await db.insert("users").values(name="Alice").execute()

        Returns:
            Transaction context manager.
        """
        self._conn_manager.check_connected()
        conn = await self._conn_manager.driver.acquire()
        return Transaction(
            self,
            self._conn_manager.driver,
            conn,
            self._conn_manager.driver.release,
        )

    # Helper methods

    async def count(self, table: str, **conditions: Any) -> int:
        """Count rows in a table with optional conditions.

        Args:
            table: Table name.
            **conditions: Column-value pairs for WHERE clause.

        Returns:
            Number of matching rows.

        Example:
            total = await db.count("users")
            active_count = await db.count("users", active=True)
        """
        query = self.select("COUNT(*) as count").from_(table)
        if conditions:
            query = query.where(**conditions)
        result = await query.fetch_one()
        return result["count"] if result else 0

    async def exists(self, table: str, **conditions: Any) -> bool:
        """Check if any rows exist in a table with optional conditions.

        Args:
            table: Table name.
            **conditions: Column-value pairs for WHERE clause.

        Returns:
            True if at least one row exists, False otherwise.

        Example:
            has_users = await db.exists("users")
            has_admin = await db.exists("users", role="admin")
        """
        return await self.count(table, **conditions) > 0

    # Internal: for Transaction to set/unset transaction connection

    def _set_transaction_connection(self, conn: Any) -> None:
        """Set the transaction connection (used by Transaction)."""
        self._conn_manager.transaction_connection = conn

    def _clear_transaction_connection(self) -> None:
        """Clear the transaction connection (used by Transaction)."""
        self._conn_manager.transaction_connection = None
