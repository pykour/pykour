"""Tests for ConnectionManager."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pykour.db.connection import ConnectionManager, get_driver
from pykour.db.exceptions import DatabaseConnectionException, DriverNotFoundException
from pykour.db.result import Row


# ---------------------------------------------------------------------------
# get_driver helper
# ---------------------------------------------------------------------------


class TestGetDriver:
    """Tests for get_driver() helper."""

    def test_sqlite_scheme(self) -> None:
        """sqlite scheme returns SQLiteDriver."""
        from pykour.db.drivers.sqlite import SQLiteDriver

        driver, name = get_driver("sqlite")
        assert isinstance(driver, SQLiteDriver)
        assert name == "sqlite"

    def test_sqlite3_scheme(self) -> None:
        """sqlite3 scheme is also accepted."""
        from pykour.db.drivers.sqlite import SQLiteDriver

        driver, name = get_driver("sqlite3")
        assert isinstance(driver, SQLiteDriver)
        assert name == "sqlite"

    def test_unknown_scheme_raises(self) -> None:
        """Unknown scheme raises DriverNotFoundException."""
        with pytest.raises(DriverNotFoundException):
            get_driver("oracle")


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------


def _make_manager(url: str = "sqlite:///test.db") -> ConnectionManager:
    """Create a ConnectionManager with a mocked driver."""
    manager = ConnectionManager(url)
    mock_driver = MagicMock()
    mock_driver.connect = AsyncMock()
    mock_driver.disconnect = AsyncMock()
    mock_driver.acquire = AsyncMock(return_value="mock_conn")
    mock_driver.release = AsyncMock()
    mock_driver.fetch_all = AsyncMock(return_value=[])
    mock_driver.fetch_one = AsyncMock(return_value=None)
    mock_driver.execute = AsyncMock(return_value=1)
    mock_driver.convert_placeholders = MagicMock(side_effect=lambda sql, n: sql)
    manager._driver = mock_driver
    return manager


class TestConnectionManagerConnect:
    """Tests for connect() / disconnect() / is_connected."""

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """connect() marks manager as connected."""
        manager = _make_manager()
        assert not manager.is_connected

        await manager.connect()

        assert manager.is_connected
        manager._driver.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_is_idempotent(self) -> None:
        """Calling connect() twice only connects once."""
        manager = _make_manager()
        await manager.connect()
        await manager.connect()

        manager._driver.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_wraps_exception(self) -> None:
        """Driver error is wrapped in DatabaseConnectionException."""
        manager = _make_manager()
        manager._driver.connect.side_effect = OSError("refused")

        with pytest.raises(DatabaseConnectionException, match="Failed to connect"):
            await manager.connect()

        assert not manager.is_connected

    @pytest.mark.asyncio
    async def test_disconnect_success(self) -> None:
        """disconnect() marks manager as disconnected."""
        manager = _make_manager()
        await manager.connect()
        await manager.disconnect()

        assert not manager.is_connected
        manager._driver.disconnect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected_is_noop(self) -> None:
        """disconnect() when not connected does nothing."""
        manager = _make_manager()
        await manager.disconnect()

        manager._driver.disconnect.assert_not_awaited()


class TestConnectionManagerCheckConnected:
    """Tests for check_connected()."""

    def test_check_connected_raises_when_not_connected(self) -> None:
        """check_connected() raises if not connected."""
        manager = _make_manager()
        with pytest.raises(DatabaseConnectionException, match="not connected"):
            manager.check_connected()

    @pytest.mark.asyncio
    async def test_check_connected_passes_when_connected(self) -> None:
        """check_connected() is silent when connected."""
        manager = _make_manager()
        await manager.connect()
        manager.check_connected()  # must not raise


class TestConnectionManagerAcquireRelease:
    """Tests for acquire() / release()."""

    @pytest.mark.asyncio
    async def test_acquire_returns_driver_connection(self) -> None:
        """acquire() returns connection from driver when no transaction active."""
        manager = _make_manager()
        conn = await manager.acquire()

        assert conn == "mock_conn"
        manager._driver.acquire.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_acquire_returns_transaction_connection(self) -> None:
        """acquire() returns transaction connection when one is set."""
        manager = _make_manager()
        manager.transaction_connection = "txn_conn"

        conn = await manager.acquire()

        assert conn == "txn_conn"
        manager._driver.acquire.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_release_calls_driver_when_no_transaction(self) -> None:
        """release() delegates to driver when no active transaction."""
        manager = _make_manager()
        await manager.release("some_conn")

        manager._driver.release.assert_awaited_once_with("some_conn")

    @pytest.mark.asyncio
    async def test_release_is_noop_during_transaction(self) -> None:
        """release() does nothing when a transaction connection is active."""
        manager = _make_manager()
        manager.transaction_connection = "txn_conn"
        await manager.release("some_conn")

        manager._driver.release.assert_not_awaited()


class TestConnectionManagerFetch:
    """Tests for fetch_all() / fetch_one() return types."""

    @pytest.mark.asyncio
    async def test_fetch_all_returns_list(self) -> None:
        """fetch_all() returns the list from the driver."""
        manager = _make_manager()
        rows = [Row({"id": 1}), Row({"id": 2})]
        manager._driver.fetch_all.return_value = rows

        result = await manager.fetch_all("conn", "SELECT 1", ())

        assert result == rows

    @pytest.mark.asyncio
    async def test_fetch_one_returns_row_or_none(self) -> None:
        """fetch_one() returns a single Row or None."""
        manager = _make_manager()
        manager._driver.fetch_one.return_value = Row({"id": 1})

        result = await manager.fetch_one("conn", "SELECT 1", ())

        assert result == Row({"id": 1})

    @pytest.mark.asyncio
    async def test_fetch_one_returns_none(self) -> None:
        """fetch_one() returns None when driver returns None."""
        manager = _make_manager()
        result = await manager.fetch_one("conn", "SELECT 1", ())

        assert result is None
