"""Connection management for Pykour database."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from pykour.db.drivers.base import BaseDriver
from pykour.db.exceptions import DatabaseConnectionException, DriverNotFoundException

if TYPE_CHECKING:
    pass


def get_driver(scheme: str) -> tuple[BaseDriver, str]:
    """Get the appropriate driver for the URL scheme.

    Args:
        scheme: URL scheme (sqlite, postgresql, mysql).

    Returns:
        Tuple of (driver instance, driver name).

    Raises:
        DriverNotFoundException: If no driver exists for the scheme.
    """
    if scheme in ("sqlite", "sqlite3"):
        from pykour.db.drivers.sqlite import SQLiteDriver

        return SQLiteDriver(), "sqlite"
    elif scheme in ("postgresql", "postgres"):
        from pykour.db.drivers.postgresql import PostgreSQLDriver

        return PostgreSQLDriver(), "postgresql"
    elif scheme == "mysql":
        from pykour.db.drivers.mysql import MySQLDriver

        return MySQLDriver(), "mysql"
    else:
        raise DriverNotFoundException(scheme)


class ConnectionManager:
    """Manages database connections and connection pooling.

    This class handles:
    - Driver initialization based on database URL
    - Connection pool management (connect/disconnect)
    - Connection acquisition and release
    - Transaction connection tracking

    Example:
        manager = ConnectionManager("sqlite:///app.db")
        await manager.connect()

        conn = await manager.acquire()
        try:
            # Use connection
            pass
        finally:
            await manager.release(conn)

        await manager.disconnect()
    """

    def __init__(
        self,
        url: str,
        min_size: int = 1,
        max_size: int = 10,
    ) -> None:
        """Initialize connection manager.

        Args:
            url: Database connection URL.
            min_size: Minimum number of connections in the pool.
            max_size: Maximum number of connections in the pool.
        """
        self._url = url
        self._min_size = min_size
        self._max_size = max_size

        parsed = urlparse(url)
        self._driver, self._driver_name = get_driver(parsed.scheme)
        self._connected = False
        self._transaction_conn: Any = None

    @property
    def driver(self) -> BaseDriver:
        """Get the database driver."""
        return self._driver

    @property
    def driver_name(self) -> str:
        """Get the database driver name."""
        return self._driver_name

    @property
    def is_connected(self) -> bool:
        """Check if connected to the database."""
        return self._connected

    @property
    def transaction_connection(self) -> Any:
        """Get the current transaction connection, if any."""
        return self._transaction_conn

    @transaction_connection.setter
    def transaction_connection(self, conn: Any) -> None:
        """Set the transaction connection."""
        self._transaction_conn = conn

    async def connect(self) -> None:
        """Connect to the database.

        Raises:
            DatabaseConnectionException: If connection fails.
        """
        if self._connected:
            return
        try:
            await self._driver.connect(self._url, self._min_size, self._max_size)
            self._connected = True
        except Exception as e:
            raise DatabaseConnectionException(f"Failed to connect: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the database."""
        if not self._connected:
            return
        await self._driver.disconnect()
        self._connected = False

    def check_connected(self) -> None:
        """Check if connected, raise if not.

        Raises:
            DatabaseConnectionException: If not connected.
        """
        if not self._connected:
            raise DatabaseConnectionException("Database not connected")

    async def acquire(self) -> Any:
        """Acquire a connection from the pool.

        If in a transaction, returns the transaction connection.

        Returns:
            Database connection.
        """
        if self._transaction_conn is not None:
            return self._transaction_conn
        return await self._driver.acquire()

    async def release(self, conn: Any) -> None:
        """Release a connection back to the pool.

        Does nothing if the connection is a transaction connection.

        Args:
            conn: Connection to release.
        """
        if self._transaction_conn is None:
            await self._driver.release(conn)

    def convert_placeholders(self, sql: str, arg_count: int) -> str:
        """Convert $N placeholders to driver-specific format.

        Args:
            sql: SQL with $1, $2, ... placeholders.
            arg_count: Number of arguments.

        Returns:
            SQL with driver-specific placeholders.
        """
        return self._driver.convert_placeholders(sql, arg_count)

    async def execute(self, conn: Any, sql: str, args: tuple[Any, ...]) -> int:
        """Execute a query on a connection.

        Args:
            conn: Database connection.
            sql: SQL query (already converted placeholders).
            args: Query arguments.

        Returns:
            Number of affected rows.
        """
        return await self._driver.execute(conn, sql, args)

    async def commit(self, conn: Any) -> None:
        """Commit changes on a connection.

        Args:
            conn: Database connection.
        """
        await self._driver.commit(conn)

    async def fetch_all(self, conn: Any, sql: str, args: tuple[Any, ...]) -> Any:
        """Fetch all rows from a query.

        Args:
            conn: Database connection.
            sql: SQL query (already converted placeholders).
            args: Query arguments.

        Returns:
            List of rows.
        """
        return await self._driver.fetch_all(conn, sql, args)

    async def fetch_one(self, conn: Any, sql: str, args: tuple[Any, ...]) -> Any:
        """Fetch one row from a query.

        Args:
            conn: Database connection.
            sql: SQL query (already converted placeholders).
            args: Query arguments.

        Returns:
            Row or None.
        """
        return await self._driver.fetch_one(conn, sql, args)
