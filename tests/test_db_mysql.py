"""Tests for MySQL driver."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pykour.db.drivers.mysql import MySQLDriver
from pykour.db.result import Row


class MockCursor:
    """Mock cursor for testing."""

    def __init__(
        self, rows: list[dict[str, Any]] | None = None, rowcount: int = 0
    ) -> None:
        self._rows = rows or []
        self.rowcount = rowcount

    async def execute(self, sql: str, args: tuple[Any, ...] = ()) -> None:
        pass

    async def fetchall(self) -> list[dict[str, Any]]:
        return self._rows

    async def fetchone(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    async def __aenter__(self) -> "MockCursor":
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass


class TestMySQLDriverProperties:
    """Tests for MySQLDriver properties."""

    def test_driver_name(self) -> None:
        """Test driver_name returns 'mysql'."""
        driver = MySQLDriver()
        assert driver.driver_name == "mysql"

    def test_placeholder_style(self) -> None:
        """Test placeholder_style returns 'percent'."""
        driver = MySQLDriver()
        assert driver.placeholder_style == "percent"

    def test_initial_pool_is_none(self) -> None:
        """Test initial pool is None."""
        driver = MySQLDriver()
        assert driver._pool is None


class TestMySQLDriverConnect:
    """Tests for MySQLDriver connect method."""

    @pytest.mark.asyncio
    async def test_connect_raises_without_aiomysql(self) -> None:
        """Test connect raises ImportError if aiomysql not installed."""
        driver = MySQLDriver()

        with patch("pykour.db.drivers.mysql.HAS_AIOMYSQL", False):
            with pytest.raises(ImportError) as exc_info:
                await driver.connect("mysql://localhost/test", 1, 5)
            assert "aiomysql is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_parses_url(self) -> None:
        """Test connect parses URL correctly."""
        driver = MySQLDriver()
        mock_pool = MagicMock()

        with patch("pykour.db.drivers.mysql.HAS_AIOMYSQL", True):
            with patch("pykour.db.drivers.mysql.aiomysql") as mock_aiomysql:
                mock_aiomysql.create_pool = AsyncMock(return_value=mock_pool)

                await driver.connect(
                    "mysql://testuser:testpass@dbhost:3307/testdb",
                    min_size=2,
                    max_size=10,
                )

                mock_aiomysql.create_pool.assert_called_once()
                call_kwargs = mock_aiomysql.create_pool.call_args[1]
                assert call_kwargs["host"] == "dbhost"
                assert call_kwargs["port"] == 3307
                assert call_kwargs["user"] == "testuser"
                assert call_kwargs["password"] == "testpass"
                assert call_kwargs["db"] == "testdb"
                assert call_kwargs["minsize"] == 2
                assert call_kwargs["maxsize"] == 10

    @pytest.mark.asyncio
    async def test_connect_default_values(self) -> None:
        """Test connect uses default values when not specified."""
        driver = MySQLDriver()
        mock_pool = MagicMock()

        with patch("pykour.db.drivers.mysql.HAS_AIOMYSQL", True):
            with patch("pykour.db.drivers.mysql.aiomysql") as mock_aiomysql:
                mock_aiomysql.create_pool = AsyncMock(return_value=mock_pool)

                await driver.connect("mysql:///testdb", min_size=1, max_size=5)

                call_kwargs = mock_aiomysql.create_pool.call_args[1]
                assert call_kwargs["host"] == "localhost"
                assert call_kwargs["port"] == 3306
                assert call_kwargs["user"] == "root"
                assert call_kwargs["password"] == ""

    @pytest.mark.asyncio
    async def test_connect_parses_charset(self) -> None:
        """Test connect parses charset from query params."""
        driver = MySQLDriver()
        mock_pool = MagicMock()

        with patch("pykour.db.drivers.mysql.HAS_AIOMYSQL", True):
            with patch("pykour.db.drivers.mysql.aiomysql") as mock_aiomysql:
                mock_aiomysql.create_pool = AsyncMock(return_value=mock_pool)

                await driver.connect(
                    "mysql://localhost/test?charset=utf8",
                    min_size=1,
                    max_size=5,
                )

                call_kwargs = mock_aiomysql.create_pool.call_args[1]
                assert call_kwargs["charset"] == "utf8"


class TestMySQLDriverDisconnect:
    """Tests for MySQLDriver disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnect_closes_pool(self) -> None:
        """Test disconnect closes and clears pool."""
        driver = MySQLDriver()
        mock_pool = MagicMock()
        mock_pool.wait_closed = AsyncMock()
        driver._pool = mock_pool

        await driver.disconnect()

        mock_pool.close.assert_called_once()
        mock_pool.wait_closed.assert_called_once()
        assert driver._pool is None

    @pytest.mark.asyncio
    async def test_disconnect_with_no_pool(self) -> None:
        """Test disconnect with no pool does nothing."""
        driver = MySQLDriver()
        driver._pool = None

        await driver.disconnect()  # Should not raise


class TestMySQLDriverAcquireRelease:
    """Tests for MySQLDriver acquire/release methods."""

    @pytest.mark.asyncio
    async def test_acquire_raises_when_not_connected(self) -> None:
        """Test acquire raises when pool is None."""
        driver = MySQLDriver()
        driver._pool = None

        with pytest.raises(RuntimeError) as exc_info:
            await driver.acquire()
        assert "Database not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_acquire_returns_connection(self) -> None:
        """Test acquire returns connection from pool."""
        driver = MySQLDriver()
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.acquire = AsyncMock(return_value=mock_conn)
        driver._pool = mock_pool

        conn = await driver.acquire()

        assert conn is mock_conn
        mock_pool.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_release_returns_connection(self) -> None:
        """Test release returns connection to pool."""
        driver = MySQLDriver()
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        driver._pool = mock_pool

        await driver.release(mock_conn)

        mock_pool.release.assert_called_once_with(mock_conn)

    @pytest.mark.asyncio
    async def test_release_with_no_pool(self) -> None:
        """Test release with no pool does nothing."""
        driver = MySQLDriver()
        driver._pool = None
        mock_conn = MagicMock()

        await driver.release(mock_conn)  # Should not raise


class TestMySQLDriverExecute:
    """Tests for MySQLDriver execute method."""

    @pytest.mark.asyncio
    async def test_execute_returns_rowcount(self) -> None:
        """Test execute returns affected row count."""
        driver = MySQLDriver()
        mock_cursor = MockCursor(rowcount=3)
        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        result = await driver.execute(
            mock_conn,
            "UPDATE users SET name = $1 WHERE id = $2",
            ("John", 1),
        )

        assert result == 3

    @pytest.mark.asyncio
    async def test_execute_converts_placeholders(self) -> None:
        """Test execute converts $n to %s placeholders."""
        driver = MySQLDriver()
        executed_sql: list[str] = []

        class CapturingCursor(MockCursor):
            async def execute(self, sql: str, args: tuple[Any, ...] = ()) -> None:
                executed_sql.append(sql)

        mock_cursor = CapturingCursor(rowcount=1)
        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        await driver.execute(
            mock_conn,
            "INSERT INTO users (name, email) VALUES ($1, $2)",
            ("John", "john@example.com"),
        )

        assert len(executed_sql) == 1
        assert "%s" in executed_sql[0]
        assert "$1" not in executed_sql[0]


class TestMySQLDriverFetch:
    """Tests for MySQLDriver fetch methods."""

    @pytest.mark.asyncio
    async def test_fetch_all_returns_rows(self) -> None:
        """Test fetch_all returns list of Row objects."""
        driver = MySQLDriver()
        mock_cursor = MockCursor(
            rows=[
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]
        )
        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        with patch("pykour.db.drivers.mysql.aiomysql"):
            result = await driver.fetch_all(mock_conn, "SELECT * FROM users", ())

        assert len(result) == 2
        assert isinstance(result[0], Row)
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_fetch_all_empty(self) -> None:
        """Test fetch_all returns empty list when no results."""
        driver = MySQLDriver()
        mock_cursor = MockCursor(rows=[])
        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        with patch("pykour.db.drivers.mysql.aiomysql"):
            result = await driver.fetch_all(mock_conn, "SELECT * FROM users", ())

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_one_returns_row(self) -> None:
        """Test fetch_one returns single Row object."""
        driver = MySQLDriver()
        mock_cursor = MockCursor(rows=[{"id": 1, "name": "Alice"}])
        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        with patch("pykour.db.drivers.mysql.aiomysql"):
            result = await driver.fetch_one(
                mock_conn,
                "SELECT * FROM users WHERE id = $1",
                (1,),
            )

        assert isinstance(result, Row)
        assert result["id"] == 1
        assert result["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_fetch_one_returns_none(self) -> None:
        """Test fetch_one returns None when no results."""
        driver = MySQLDriver()
        mock_cursor = MockCursor(rows=[])
        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        with patch("pykour.db.drivers.mysql.aiomysql"):
            result = await driver.fetch_one(
                mock_conn,
                "SELECT * FROM users WHERE id = $1",
                (999,),
            )

        assert result is None


class TestMySQLDriverTransaction:
    """Tests for MySQLDriver transaction methods."""

    @pytest.mark.asyncio
    async def test_begin(self) -> None:
        """Test begin calls conn.begin()."""
        driver = MySQLDriver()
        mock_conn = MagicMock()
        mock_conn.begin = AsyncMock()

        await driver.begin(mock_conn)

        mock_conn.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit(self) -> None:
        """Test commit calls conn.commit()."""
        driver = MySQLDriver()
        mock_conn = MagicMock()
        mock_conn.commit = AsyncMock()

        await driver.commit(mock_conn)

        mock_conn.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback(self) -> None:
        """Test rollback calls conn.rollback()."""
        driver = MySQLDriver()
        mock_conn = MagicMock()
        mock_conn.rollback = AsyncMock()

        await driver.rollback(mock_conn)

        mock_conn.rollback.assert_called_once()
