"""MySQL driver using aiomysql."""

from typing import Any
from urllib.parse import parse_qs, urlparse

from pykour.db.drivers.base import BaseDriver
from pykour.db.result import Row

try:
    import aiomysql

    HAS_AIOMYSQL = True
except ImportError:
    HAS_AIOMYSQL = False


class MySQLDriver(BaseDriver):
    """MySQL driver using aiomysql.

    Supports connection URLs in the format:
        mysql://user:password@host:port/database
    """

    def __init__(self) -> None:
        self._pool: "aiomysql.Pool | None" = None

    @property
    def driver_name(self) -> str:
        """Return the canonical driver name."""
        return "mysql"

    @property
    def placeholder_style(self) -> str:
        """MySQL uses %s placeholders."""
        return "percent"

    async def connect(
        self,
        url: str,
        min_size: int,
        max_size: int,
    ) -> None:
        """Connect to MySQL database."""
        if not HAS_AIOMYSQL:
            raise ImportError(
                "aiomysql is required for MySQL support. "
                "Install it with: pip install aiomysql"
            )

        parsed = urlparse(url)

        # Extract connection parameters
        host = parsed.hostname or "localhost"
        port = parsed.port or 3306
        user = parsed.username or "root"
        password = parsed.password or ""
        database = parsed.path.lstrip("/") or None

        # Parse query parameters
        query_params = parse_qs(parsed.query)
        charset = query_params.get("charset", ["utf8mb4"])[0]

        self._pool = await aiomysql.create_pool(
            host=host,
            port=port,
            user=user,
            password=password,
            db=database,
            charset=charset,
            minsize=min_size,
            maxsize=max_size,
            autocommit=True,
        )

    async def disconnect(self) -> None:
        """Close the connection pool."""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def acquire(self) -> Any:
        """Acquire a connection from the pool."""
        if self._pool is None:
            raise RuntimeError("Database not connected")
        return await self._pool.acquire()

    async def release(self, conn: Any) -> None:
        """Release a connection back to the pool."""
        if self._pool:
            self._pool.release(conn)

    async def execute(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> int:
        """Execute a query without returning results."""
        converted_sql = self.convert_placeholders(sql, len(args))
        async with conn.cursor() as cursor:
            await cursor.execute(converted_sql, args)
            return cursor.rowcount

    async def fetch_all(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> list[Row]:
        """Fetch all rows from a query."""
        converted_sql = self.convert_placeholders(sql, len(args))
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(converted_sql, args)
            rows = await cursor.fetchall()
            return [Row(row) for row in rows]

    async def fetch_one(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> Row | None:
        """Fetch a single row from a query."""
        converted_sql = self.convert_placeholders(sql, len(args))
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(converted_sql, args)
            row = await cursor.fetchone()
            return Row(row) if row else None

    async def begin(self, conn: Any, isolation_level: str | None = None) -> None:
        """Begin a transaction."""
        if isolation_level:
            async with conn.cursor() as cur:
                await cur.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
            await conn.begin()
        else:
            await conn.begin()

    async def commit(self, conn: Any) -> None:
        """Commit a transaction."""
        await conn.commit()

    async def rollback(self, conn: Any) -> None:
        """Rollback a transaction."""
        await conn.rollback()
