"""Tests for PostgreSQL driver."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pykour.db.drivers.postgresql import PostgreSQLDriver
from pykour.db.result import Row


class MockRecord:
    """Mock asyncpg Record for testing."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __iter__(self) -> Any:
        return iter(self._data.items())

    def keys(self) -> Any:
        return self._data.keys()

    def values(self) -> Any:
        return self._data.values()

    def items(self) -> Any:
        return self._data.items()

    def __getitem__(self, key: str) -> Any:
        return self._data[key]


class TestPostgreSQLDriverProperties:
    """Tests for PostgreSQLDriver properties."""

    def test_driver_name(self) -> None:
        """Test driver_name returns 'postgresql'."""
        driver = PostgreSQLDriver()
        assert driver.driver_name == "postgresql"

    def test_placeholder_style(self) -> None:
        """Test placeholder_style returns 'dollar'."""
        driver = PostgreSQLDriver()
        assert driver.placeholder_style == "dollar"

    def test_initial_pool_is_none(self) -> None:
        """Test initial pool is None."""
        driver = PostgreSQLDriver()
        assert driver._pool is None


class TestPostgreSQLDriverConnect:
    """Tests for PostgreSQLDriver connect method."""

    @pytest.mark.asyncio
    async def test_connect_raises_without_asyncpg(self) -> None:
        """Test connect raises ImportError if asyncpg not installed."""
        driver = PostgreSQLDriver()

        with patch("pykour.db.drivers.postgresql.HAS_ASYNCPG", False):
            with pytest.raises(ImportError) as exc_info:
                await driver.connect("postgresql://localhost/test", 1, 5)
            assert "asyncpg is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_with_postgresql_url(self) -> None:
        """Test connect with postgresql:// URL."""
        driver = PostgreSQLDriver()
        mock_pool = MagicMock()

        with patch("pykour.db.drivers.postgresql.HAS_ASYNCPG", True):
            with patch("pykour.db.drivers.postgresql.asyncpg") as mock_asyncpg:
                mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

                await driver.connect(
                    "postgresql://user:pass@host:5432/db",
                    min_size=2,
                    max_size=10,
                )

                mock_asyncpg.create_pool.assert_called_once_with(
                    "postgresql://user:pass@host:5432/db",
                    min_size=2,
                    max_size=10,
                )
                assert driver._pool is mock_pool

    @pytest.mark.asyncio
    async def test_connect_converts_postgres_url(self) -> None:
        """Test connect converts postgres:// to postgresql://."""
        driver = PostgreSQLDriver()
        mock_pool = MagicMock()

        with patch("pykour.db.drivers.postgresql.HAS_ASYNCPG", True):
            with patch("pykour.db.drivers.postgresql.asyncpg") as mock_asyncpg:
                mock_asyncpg.create_pool = AsyncMock(return_value=mock_pool)

                await driver.connect(
                    "postgres://user:pass@host:5432/db",
                    min_size=1,
                    max_size=5,
                )

                # Check that URL was converted
                call_args = mock_asyncpg.create_pool.call_args[0]
                assert call_args[0] == "postgresql://user:pass@host:5432/db"


class TestPostgreSQLDriverDisconnect:
    """Tests for PostgreSQLDriver disconnect method."""

    @pytest.mark.asyncio
    async def test_disconnect_closes_pool(self) -> None:
        """Test disconnect closes and clears pool."""
        driver = PostgreSQLDriver()
        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()
        driver._pool = mock_pool

        await driver.disconnect()

        mock_pool.close.assert_called_once()
        assert driver._pool is None

    @pytest.mark.asyncio
    async def test_disconnect_with_no_pool(self) -> None:
        """Test disconnect with no pool does nothing."""
        driver = PostgreSQLDriver()
        driver._pool = None

        await driver.disconnect()  # Should not raise


class TestPostgreSQLDriverAcquireRelease:
    """Tests for PostgreSQLDriver acquire/release methods."""

    @pytest.mark.asyncio
    async def test_acquire_raises_when_not_connected(self) -> None:
        """Test acquire raises when pool is None."""
        driver = PostgreSQLDriver()
        driver._pool = None

        with pytest.raises(RuntimeError) as exc_info:
            await driver.acquire()
        assert "Database not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_acquire_returns_connection(self) -> None:
        """Test acquire returns connection from pool."""
        driver = PostgreSQLDriver()
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
        driver = PostgreSQLDriver()
        mock_pool = MagicMock()
        mock_pool.release = AsyncMock()
        mock_conn = MagicMock()
        driver._pool = mock_pool

        await driver.release(mock_conn)

        mock_pool.release.assert_called_once_with(mock_conn)

    @pytest.mark.asyncio
    async def test_release_with_no_pool(self) -> None:
        """Test release with no pool does nothing."""
        driver = PostgreSQLDriver()
        driver._pool = None
        mock_conn = MagicMock()

        await driver.release(mock_conn)  # Should not raise


class TestPostgreSQLDriverExecute:
    """Tests for PostgreSQLDriver execute method."""

    @pytest.mark.asyncio
    async def test_execute_returns_rowcount_from_insert(self) -> None:
        """Test execute parses 'INSERT 0 1' result."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 0 1")

        result = await driver.execute(
            mock_conn,
            "INSERT INTO users (name) VALUES ($1)",
            ("John",),
        )

        assert result == 1

    @pytest.mark.asyncio
    async def test_execute_returns_rowcount_from_update(self) -> None:
        """Test execute parses 'UPDATE 3' result."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="UPDATE 3")

        result = await driver.execute(
            mock_conn,
            "UPDATE users SET active = $1",
            (True,),
        )

        assert result == 3

    @pytest.mark.asyncio
    async def test_execute_returns_rowcount_from_delete(self) -> None:
        """Test execute parses 'DELETE 5' result."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="DELETE 5")

        result = await driver.execute(
            mock_conn,
            "DELETE FROM users WHERE active = $1",
            (False,),
        )

        assert result == 5

    @pytest.mark.asyncio
    async def test_execute_returns_zero_for_no_result(self) -> None:
        """Test execute returns 0 when no result."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value=None)

        result = await driver.execute(mock_conn, "CREATE TABLE test (id INT)", ())

        assert result == 0

    @pytest.mark.asyncio
    async def test_execute_returns_zero_for_invalid_result(self) -> None:
        """Test execute returns 0 for non-numeric result."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="SELECT")

        result = await driver.execute(mock_conn, "SELECT 1", ())

        assert result == 0

    @pytest.mark.asyncio
    async def test_execute_spreads_args(self) -> None:
        """Test execute spreads args correctly."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock(return_value="INSERT 0 1")

        await driver.execute(
            mock_conn,
            "INSERT INTO users (name, email) VALUES ($1, $2)",
            ("John", "john@example.com"),
        )

        mock_conn.execute.assert_called_once_with(
            "INSERT INTO users (name, email) VALUES ($1, $2)",
            "John",
            "john@example.com",
        )


class TestPostgreSQLDriverFetch:
    """Tests for PostgreSQLDriver fetch methods."""

    @pytest.mark.asyncio
    async def test_fetch_all_returns_rows(self) -> None:
        """Test fetch_all returns list of Row objects."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[
            MockRecord({"id": 1, "name": "Alice"}),
            MockRecord({"id": 2, "name": "Bob"}),
        ])

        result = await driver.fetch_all(mock_conn, "SELECT * FROM users", ())

        assert len(result) == 2
        assert isinstance(result[0], Row)
        assert result[0]["name"] == "Alice"
        assert result[1]["name"] == "Bob"

    @pytest.mark.asyncio
    async def test_fetch_all_empty(self) -> None:
        """Test fetch_all returns empty list when no results."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        result = await driver.fetch_all(mock_conn, "SELECT * FROM users", ())

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_all_spreads_args(self) -> None:
        """Test fetch_all spreads args correctly."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.fetch = AsyncMock(return_value=[])

        await driver.fetch_all(
            mock_conn,
            "SELECT * FROM users WHERE name = $1 AND active = $2",
            ("John", True),
        )

        mock_conn.fetch.assert_called_once_with(
            "SELECT * FROM users WHERE name = $1 AND active = $2",
            "John",
            True,
        )

    @pytest.mark.asyncio
    async def test_fetch_one_returns_row(self) -> None:
        """Test fetch_one returns single Row object."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(
            return_value=MockRecord({"id": 1, "name": "Alice"})
        )

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
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        result = await driver.fetch_one(
            mock_conn,
            "SELECT * FROM users WHERE id = $1",
            (999,),
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_one_spreads_args(self) -> None:
        """Test fetch_one spreads args correctly."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.fetchrow = AsyncMock(return_value=None)

        await driver.fetch_one(
            mock_conn,
            "SELECT * FROM users WHERE id = $1",
            (1,),
        )

        mock_conn.fetchrow.assert_called_once_with(
            "SELECT * FROM users WHERE id = $1",
            1,
        )


class TestPostgreSQLDriverTransaction:
    """Tests for PostgreSQLDriver transaction methods."""

    @pytest.mark.asyncio
    async def test_begin(self) -> None:
        """Test begin executes BEGIN."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        await driver.begin(mock_conn)

        mock_conn.execute.assert_called_once_with("BEGIN")

    @pytest.mark.asyncio
    async def test_commit(self) -> None:
        """Test commit executes COMMIT."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        await driver.commit(mock_conn)

        mock_conn.execute.assert_called_once_with("COMMIT")

    @pytest.mark.asyncio
    async def test_rollback(self) -> None:
        """Test rollback executes ROLLBACK."""
        driver = PostgreSQLDriver()
        mock_conn = MagicMock()
        mock_conn.execute = AsyncMock()

        await driver.rollback(mock_conn)

        mock_conn.execute.assert_called_once_with("ROLLBACK")
