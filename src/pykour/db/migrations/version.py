"""Migration version management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pykour.db.drivers.base import BaseDriver


MIGRATIONS_TABLE = "_pykour_migrations"


@dataclass
class MigrationRecord:
    """A record of an applied migration."""

    version: str
    name: str
    applied_at: datetime


class VersionManager:
    """Manages migration version tracking in the database."""

    def __init__(self, driver: BaseDriver) -> None:
        self._driver = driver

    async def init(self, conn: Any) -> None:
        """Create the migrations table if it doesn't exist."""
        driver_name = self._driver.driver_name

        # PostgreSQL and MySQL use the same schema
        if driver_name in ("postgresql", "mysql"):
            sql = f"""
                CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                    version VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
        else:
            # SQLite
            sql = f"""
                CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                    version TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """

        await conn.execute(sql)
        await self._driver.commit(conn)

    async def get_applied(self, conn: Any) -> list[MigrationRecord]:
        """Get all applied migrations ordered by version."""
        sql = (
            f"SELECT version, name, applied_at FROM {MIGRATIONS_TABLE} ORDER BY version"
        )
        rows = await self._driver.fetch_all(conn, sql, ())
        return [
            MigrationRecord(
                version=row["version"],
                name=row["name"],
                applied_at=self._parse_applied_at(row["applied_at"], row["version"]),
            )
            for row in rows
        ]

    def _parse_applied_at(self, value: Any, version: str) -> datetime:
        """Parse applied_at value to datetime.

        Args:
            value: The applied_at value from the database row.
            version: The migration version (for error messages).

        Returns:
            Parsed datetime value.

        Raises:
            ValueError: If the value is not a datetime or valid ISO format string.
        """
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError as e:
                raise ValueError(
                    f"Invalid applied_at format for migration {version}: "
                    f"cannot parse '{value}' as ISO datetime"
                ) from e
        raise ValueError(
            f"Invalid applied_at type for migration {version}: "
            f"expected datetime or str, got {type(value).__name__}"
        )

    async def get_applied_versions(self, conn: Any) -> set[str]:
        """Get the set of applied migration versions."""
        records = await self.get_applied(conn)
        return {r.version for r in records}

    async def get_current_version(self, conn: Any) -> str | None:
        """Get the current (latest) migration version."""
        sql = f"SELECT version FROM {MIGRATIONS_TABLE} ORDER BY version DESC LIMIT 1"
        row = await self._driver.fetch_one(conn, sql, ())
        return row["version"] if row else None

    async def mark_applied(self, conn: Any, version: str, name: str) -> None:
        """Mark a migration as applied."""
        driver_name = self._driver.driver_name

        if driver_name == "postgresql":
            sql = f"INSERT INTO {MIGRATIONS_TABLE} (version, name) VALUES ($1, $2)"
        elif driver_name == "mysql":
            sql = f"INSERT INTO {MIGRATIONS_TABLE} (version, name) VALUES (%s, %s)"
        else:
            sql = f"INSERT INTO {MIGRATIONS_TABLE} (version, name) VALUES (?, ?)"

        await self._driver.execute(conn, sql, (version, name))
        await self._driver.commit(conn)

    async def mark_unapplied(self, conn: Any, version: str) -> None:
        """Remove a migration from the applied list."""
        driver_name = self._driver.driver_name

        if driver_name == "postgresql":
            sql = f"DELETE FROM {MIGRATIONS_TABLE} WHERE version = $1"
        elif driver_name == "mysql":
            sql = f"DELETE FROM {MIGRATIONS_TABLE} WHERE version = %s"
        else:
            sql = f"DELETE FROM {MIGRATIONS_TABLE} WHERE version = ?"

        await self._driver.execute(conn, sql, (version,))
        await self._driver.commit(conn)

    async def is_applied(self, conn: Any, version: str) -> bool:
        """Check if a migration has been applied."""
        driver_name = self._driver.driver_name

        if driver_name == "postgresql":
            sql = f"SELECT 1 FROM {MIGRATIONS_TABLE} WHERE version = $1"
        elif driver_name == "mysql":
            sql = f"SELECT 1 FROM {MIGRATIONS_TABLE} WHERE version = %s"
        else:
            sql = f"SELECT 1 FROM {MIGRATIONS_TABLE} WHERE version = ?"

        row = await self._driver.fetch_one(conn, sql, (version,))
        return row is not None
