"""PostgreSQL driver using asyncpg."""

from typing import Any

from pykour.db.drivers.base import BaseDriver
from pykour.db.result import Row

try:
    import asyncpg

    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False


class PostgreSQLDriver(BaseDriver):
    """PostgreSQL driver using asyncpg.

    Supports connection URLs in the format:
        postgresql://user:password@host:port/database
        postgres://user:password@host:port/database
    """

    def __init__(self) -> None:
        self._pool: "asyncpg.Pool | None" = None

    @property
    def driver_name(self) -> str:
        """Return the canonical driver name."""
        return "postgresql"

    @property
    def placeholder_style(self) -> str:
        """PostgreSQL uses $1, $2, ... placeholders."""
        return "dollar"

    async def connect(
        self,
        url: str,
        min_size: int,
        max_size: int,
    ) -> None:
        """Connect to PostgreSQL database."""
        if not HAS_ASYNCPG:
            raise ImportError(
                "asyncpg is required for PostgreSQL support. "
                "Install it with: pip install asyncpg"
            )

        # Convert postgres:// to postgresql:// if needed
        if url.startswith("postgres://"):
            url = "postgresql://" + url[11:]

        self._pool = await asyncpg.create_pool(
            url,
            min_size=min_size,
            max_size=max_size,
        )

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def acquire(self) -> Any:
        """Acquire a connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        return await self._pool.acquire()

    async def release(self, conn: Any) -> None:
        """Release a connection back to the pool."""
        if self._pool:
            await self._pool.release(conn)

    async def execute(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> int:
        """Execute a query without returning results."""
        result = await conn.execute(sql, *args)
        # asyncpg returns "INSERT 0 1" or "UPDATE 1" etc.
        if result:
            parts = result.split()
            if len(parts) >= 2 and parts[-1].isdigit():
                return int(parts[-1])
        return 0

    async def fetch_all(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> list[Row]:
        """Fetch all rows from a query."""
        records = await conn.fetch(sql, *args)
        return [Row(dict(record)) for record in records]

    async def fetch_one(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> Row | None:
        """Fetch a single row from a query."""
        record = await conn.fetchrow(sql, *args)
        return Row(dict(record)) if record else None

    async def begin(self, conn: Any, isolation_level: str | None = None) -> None:
        """Begin a transaction."""
        if isolation_level:
            await conn.execute(f"BEGIN TRANSACTION ISOLATION LEVEL {isolation_level}")
        else:
            await conn.execute("BEGIN")

    async def commit(self, conn: Any) -> None:
        """Commit a transaction."""
        await conn.execute("COMMIT")

    async def rollback(self, conn: Any) -> None:
        """Rollback a transaction."""
        await conn.execute("ROLLBACK")
