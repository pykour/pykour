"""Base driver interface."""

import re
from abc import ABC, abstractmethod
from typing import Any, Literal

from pykour.db.result import Row

IsolationLevel = Literal[
    "READ UNCOMMITTED",
    "READ COMMITTED",
    "REPEATABLE READ",
    "SERIALIZABLE",
]


class BaseDriver(ABC):
    """Abstract base class for database drivers.

    Each database driver must implement this interface to provide
    a consistent API across different databases.
    """

    @property
    @abstractmethod
    def driver_name(self) -> str:
        """Return the canonical name of this driver.

        Returns:
            "sqlite", "postgresql", or "mysql"
        """

    @property
    @abstractmethod
    def placeholder_style(self) -> str:
        """Return the placeholder style for this driver.

        Returns:
            "dollar" for PostgreSQL ($1, $2, ...)
            "percent" for MySQL (%s, %s, ...)
            "qmark" for SQLite (?, ?, ...)
        """

    @abstractmethod
    async def connect(
        self,
        url: str,
        min_size: int,
        max_size: int,
    ) -> None:
        """Connect to the database and create connection pool.

        Args:
            url: Database connection URL.
            min_size: Minimum number of connections in the pool.
            max_size: Maximum number of connections in the pool.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close all connections and clean up resources."""

    @abstractmethod
    async def acquire(self) -> Any:
        """Acquire a connection from the pool.

        Returns:
            A database connection object.
        """

    @abstractmethod
    async def release(self, conn: Any) -> None:
        """Release a connection back to the pool.

        Args:
            conn: The connection to release.
        """

    @abstractmethod
    async def execute(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> int:
        """Execute a query without returning results.

        Args:
            conn: Database connection.
            sql: SQL query with placeholders.
            args: Query parameters.

        Returns:
            Number of affected rows.
        """

    @abstractmethod
    async def fetch_all(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> list[Row]:
        """Fetch all rows from a query.

        Args:
            conn: Database connection.
            sql: SQL query with placeholders.
            args: Query parameters.

        Returns:
            List of Row objects.
        """

    @abstractmethod
    async def fetch_one(
        self,
        conn: Any,
        sql: str,
        args: tuple[Any, ...],
    ) -> Row | None:
        """Fetch a single row from a query.

        Args:
            conn: Database connection.
            sql: SQL query with placeholders.
            args: Query parameters.

        Returns:
            A Row object or None if no results.
        """

    @abstractmethod
    async def begin(self, conn: Any, isolation_level: str | None = None) -> None:
        """Begin a transaction.

        Args:
            conn: Database connection.
            isolation_level: Optional isolation level for the transaction.
        """

    @abstractmethod
    async def commit(self, conn: Any) -> None:
        """Commit a transaction.

        Args:
            conn: Database connection.
        """

    @abstractmethod
    async def rollback(self, conn: Any) -> None:
        """Rollback a transaction.

        Args:
            conn: Database connection.
        """

    def convert_placeholders(self, sql: str, param_count: int) -> str:
        """Convert $1, $2, ... style placeholders to driver-specific style.

        Only replaces placeholders outside of string literals to avoid
        corrupting SQL strings that contain dollar signs.

        Args:
            sql: SQL with $1, $2, ... placeholders.
            param_count: Number of parameters.

        Returns:
            SQL with converted placeholders.

        Raises:
            ValueError: If placeholder_style is not supported.
        """
        if self.placeholder_style == "dollar":
            # PostgreSQL style, no conversion needed
            return sql
        elif self.placeholder_style == "percent":
            # MySQL style: $1 -> %s
            return self._replace_placeholders_safely(sql, param_count, "%s")
        elif self.placeholder_style == "qmark":
            # SQLite style: $1 -> ?
            return self._replace_placeholders_safely(sql, param_count, "?")
        else:
            raise ValueError(
                f"Unsupported placeholder_style: {self.placeholder_style!r}. "
                f"Supported styles: 'dollar', 'percent', 'qmark'."
            )

    def _replace_placeholders_safely(
        self, sql: str, param_count: int, replacement: str
    ) -> str:
        """Replace $N placeholders while skipping string literals.

        Args:
            sql: SQL with $1, $2, ... placeholders.
            param_count: Number of parameters.
            replacement: The replacement string ('%s' or '?').

        Returns:
            SQL with placeholders replaced outside of string literals.
        """
        # Build a pattern that matches:
        # 1. Single-quoted strings (including escaped quotes '')
        # 2. Double-quoted strings (including escaped quotes "")
        # 3. $N placeholders
        pattern = re.compile(
            r"'(?:[^']|'')*'"  # Single-quoted string
            r'|"(?:[^"]|"")*"'  # Double-quoted string
            r"|(\$(\d+))"  # $N placeholder (captured in groups 1 and 2)
        )

        def replacer(match: re.Match[str]) -> str:
            # If group 1 is None, we matched a string literal - return as-is
            if match.group(1) is None:
                return match.group(0)
            # Otherwise, replace $N with the driver-specific placeholder
            return replacement

        return pattern.sub(replacer, sql)
