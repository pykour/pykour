"""SQLite driver using aiosqlite."""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

from pykour.db.drivers.base import BaseDriver
from pykour.db.result import Row

logger = logging.getLogger(__name__)

try:
    import aiosqlite

    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False


class SQLiteDriver(BaseDriver):
    """SQLite driver using aiosqlite.

    Supports connection URLs in the format:
        sqlite:///path/to/database.db
        sqlite:///:memory:
    """

    def __init__(self) -> None:
        # Use Any for connection types to avoid NameError when aiosqlite isn't installed
        self._pool: list[Any] = []
        self._available: asyncio.Queue[Any] | None = None
        self._db_path: str = ""
        self._max_size: int = 1
        self._lock: asyncio.Lock = asyncio.Lock()

    @property
    def driver_name(self) -> str:
        """Return the canonical driver name."""
        return "sqlite"

    @property
    def placeholder_style(self) -> str:
        """SQLite uses ? placeholders."""
        return "qmark"

    async def connect(
        self,
        url: str,
        min_size: int,
        max_size: int,
    ) -> None:
        """Connect to SQLite database.

        Args:
            url: Database URL (sqlite:///path/to/db.sqlite or sqlite:///:memory:)
            min_size: Minimum pool size (ignored for SQLite).
            max_size: Maximum pool size.
        """
        if not HAS_AIOSQLITE:
            raise ImportError(
                "aiosqlite is required for SQLite support. "
                "Install it with: pip install aiosqlite"
            )

        parsed = urlparse(url)
        # Handle sqlite:///path/to/db or sqlite:///:memory:
        if parsed.netloc:
            self._db_path = f"{parsed.netloc}{parsed.path}"
        else:
            path = parsed.path
            if not path:
                self._db_path = ":memory:"
            elif path.startswith("//"):
                # Absolute path: sqlite:////abs/path.db -> path='//abs/path.db' -> '/abs/path.db'
                self._db_path = path[1:]
            else:
                # Relative path: sqlite:///rel.db -> path='/rel.db' -> 'rel.db'
                self._db_path = path.lstrip("/") or ":memory:"

        self._max_size = max_size
        self._available = asyncio.Queue(maxsize=max_size)

        # Create initial connections
        for _ in range(min(min_size, max_size)):
            conn = await aiosqlite.connect(self._db_path)
            conn.row_factory = aiosqlite.Row
            self._pool.append(conn)
            await self._available.put(conn)

    async def disconnect(self) -> None:
        """Close all connections."""
        for conn in self._pool:
            await conn.close()
        self._pool.clear()
        self._available = None

    async def acquire(self) -> Any:
        """Acquire a connection from the pool.

        Uses a lock to prevent race conditions when expanding the pool,
        ensuring we never exceed _max_size connections.
        """
        if self._available is None:
            raise RuntimeError("Database not connected")

        try:
            # Try to get from pool without waiting
            return self._available.get_nowait()
        except asyncio.QueueEmpty:
            # Use lock to safely check and expand pool
            async with self._lock:
                # Re-check if a connection became available while waiting for lock
                try:
                    return self._available.get_nowait()
                except asyncio.QueueEmpty:
                    pass

                # Create new connection if still under limit
                if len(self._pool) < self._max_size:
                    conn = await aiosqlite.connect(self._db_path)
                    conn.row_factory = aiosqlite.Row
                    self._pool.append(conn)
                    return conn

            # Max reached, wait for available connection (outside lock)
            return await self._available.get()

    async def release(self, conn: Any) -> None:
        """Release a connection back to the pool."""
        if self._available is not None:
            await self._available.put(conn)

    async def execute(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> int:
        """Execute a query without returning results.

        Note: Does not auto-commit. The caller (Database) is responsible
        for committing when not in a transaction.
        """
        converted_sql = self.convert_placeholders(sql, len(args))
        cursor = await conn.execute(converted_sql, args)
        return cursor.rowcount

    async def fetch_all(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> list[Row]:
        """Fetch all rows from a query."""
        converted_sql = self.convert_placeholders(sql, len(args))
        cursor = await conn.execute(converted_sql, args)
        rows = await cursor.fetchall()
        return [Row(dict(row)) for row in rows]

    async def fetch_one(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> Row | None:
        """Fetch a single row from a query."""
        converted_sql = self.convert_placeholders(sql, len(args))
        cursor = await conn.execute(converted_sql, args)
        row = await cursor.fetchone()
        return Row(dict(row)) if row else None

    async def begin(self, conn: Any, isolation_level: str | None = None) -> None:
        """Begin a transaction."""
        if isolation_level and isolation_level != "SERIALIZABLE":
            logger.warning(
                "SQLite does not support isolation level '%s'. "
                "Falling back to default (SERIALIZABLE).",
                isolation_level,
            )
        await conn.execute("BEGIN")

    async def commit(self, conn: Any) -> None:
        """Commit a transaction."""
        await conn.commit()

    async def rollback(self, conn: Any) -> None:
        """Rollback a transaction."""
        await conn.rollback()
