"""Tests for pykour.core.lifespan module."""

from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pykour.core.lifespan import LifespanManager


class TestLifespanManager:
    """Tests for LifespanManager class."""

    @pytest.fixture
    def mock_database(self) -> AsyncMock:
        """Create a mock database."""
        db = AsyncMock()
        db.connect = AsyncMock()
        db.disconnect = AsyncMock()
        return db

    @pytest.fixture
    def mock_cache(self) -> AsyncMock:
        """Create a mock cache storage."""
        cache = AsyncMock()
        cache.connect = AsyncMock()
        cache.disconnect = AsyncMock()
        return cache

    @pytest.fixture
    def mock_build_middleware(self) -> MagicMock:
        """Create a mock middleware builder."""
        builder = MagicMock()
        builder.return_value = MagicMock(name="middleware_app")
        return builder


class TestStartup(TestLifespanManager):
    """Tests for LifespanManager.startup method."""

    @pytest.mark.asyncio
    async def test_startup_connects_database(
        self, mock_database: AsyncMock, mock_build_middleware: MagicMock
    ) -> None:
        """Should connect database on startup."""
        manager = LifespanManager(mock_database, None, mock_build_middleware)

        await manager.startup()

        mock_database.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_connects_cache(
        self, mock_cache: AsyncMock, mock_build_middleware: MagicMock
    ) -> None:
        """Should connect cache on startup."""
        manager = LifespanManager(None, mock_cache, mock_build_middleware)

        await manager.startup()

        mock_cache.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_builds_middleware(
        self, mock_build_middleware: MagicMock
    ) -> None:
        """Should build middleware stack on startup."""
        manager = LifespanManager(None, None, mock_build_middleware)

        await manager.startup()

        mock_build_middleware.assert_called_once()
        assert manager.app is not None

    @pytest.mark.asyncio
    async def test_startup_sets_started_flag(
        self, mock_build_middleware: MagicMock
    ) -> None:
        """Should set started flag after startup."""
        manager = LifespanManager(None, None, mock_build_middleware)

        assert manager.started is False
        await manager.startup()
        assert manager.started is True

    @pytest.mark.asyncio
    async def test_startup_idempotent(
        self,
        mock_database: AsyncMock,
        mock_cache: AsyncMock,
        mock_build_middleware: MagicMock,
    ) -> None:
        """Should only run startup once even if called multiple times."""
        manager = LifespanManager(mock_database, mock_cache, mock_build_middleware)

        await manager.startup()
        await manager.startup()
        await manager.startup()

        mock_database.connect.assert_called_once()
        mock_cache.connect.assert_called_once()
        mock_build_middleware.assert_called_once()

    @pytest.mark.asyncio
    async def test_startup_concurrent_safety(
        self,
        mock_database: AsyncMock,
        mock_build_middleware: MagicMock,
    ) -> None:
        """Should handle concurrent startup calls safely."""

        # Make connect take some time to simulate race condition window
        async def slow_connect() -> None:
            await asyncio.sleep(0.01)

        mock_database.connect = AsyncMock(side_effect=slow_connect)

        manager = LifespanManager(mock_database, None, mock_build_middleware)

        # Start multiple concurrent startups
        results = await asyncio.gather(
            manager.startup(),
            manager.startup(),
            manager.startup(),
        )

        # All results should be the same app instance
        assert all(r is results[0] for r in results)
        # Connect should only be called once
        mock_database.connect.assert_called_once()


class TestShutdown(TestLifespanManager):
    """Tests for LifespanManager.shutdown method."""

    @pytest.mark.asyncio
    async def test_shutdown_disconnects_database(
        self, mock_database: AsyncMock, mock_build_middleware: MagicMock
    ) -> None:
        """Should disconnect database on shutdown."""
        manager = LifespanManager(mock_database, None, mock_build_middleware)
        await manager.startup()

        await manager.shutdown()

        mock_database.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_disconnects_cache(
        self, mock_cache: AsyncMock, mock_build_middleware: MagicMock
    ) -> None:
        """Should disconnect cache on shutdown."""
        manager = LifespanManager(None, mock_cache, mock_build_middleware)
        await manager.startup()

        await manager.shutdown()

        mock_cache.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_clears_started_flag(
        self, mock_build_middleware: MagicMock
    ) -> None:
        """Should clear started flag after shutdown."""
        manager = LifespanManager(None, None, mock_build_middleware)
        await manager.startup()

        assert manager.started is True
        await manager.shutdown()
        assert manager.started is False

    @pytest.mark.asyncio
    async def test_shutdown_without_startup_is_noop(
        self,
        mock_database: AsyncMock,
        mock_cache: AsyncMock,
        mock_build_middleware: MagicMock,
    ) -> None:
        """Should do nothing if shutdown called without startup."""
        manager = LifespanManager(mock_database, mock_cache, mock_build_middleware)

        await manager.shutdown()

        mock_database.disconnect.assert_not_called()
        mock_cache.disconnect.assert_not_called()


class TestHandleLifespan(TestLifespanManager):
    """Tests for LifespanManager.handle_lifespan method."""

    @pytest.mark.asyncio
    async def test_handle_startup_complete(
        self, mock_build_middleware: MagicMock
    ) -> None:
        """Should send startup.complete on successful startup."""
        manager = LifespanManager(None, None, mock_build_middleware)

        messages: list[dict[str, Any]] = [
            {"type": "lifespan.startup"},
            {"type": "lifespan.shutdown"},
        ]
        sent: list[MutableMapping[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return messages.pop(0)

        async def send(message: MutableMapping[str, Any]) -> None:
            sent.append(message)

        await manager.handle_lifespan({}, receive, send)

        assert {"type": "lifespan.startup.complete"} in sent
        assert {"type": "lifespan.shutdown.complete"} in sent

    @pytest.mark.asyncio
    async def test_handle_startup_failed(
        self, mock_database: AsyncMock, mock_build_middleware: MagicMock
    ) -> None:
        """Should send startup.failed on startup error."""
        mock_database.connect = AsyncMock(side_effect=Exception("Connection failed"))
        manager = LifespanManager(mock_database, None, mock_build_middleware)

        messages: list[dict[str, Any]] = [{"type": "lifespan.startup"}]
        sent: list[MutableMapping[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return messages.pop(0)

        async def send(message: MutableMapping[str, Any]) -> None:
            sent.append(message)

        await manager.handle_lifespan({}, receive, send)

        assert len(sent) == 1
        assert sent[0]["type"] == "lifespan.startup.failed"
        assert "Connection failed" in sent[0]["message"]

    @pytest.mark.asyncio
    async def test_handle_shutdown_error_still_completes(
        self, mock_database: AsyncMock, mock_build_middleware: MagicMock
    ) -> None:
        """Should send shutdown.complete even if shutdown fails."""
        mock_database.disconnect = AsyncMock(side_effect=Exception("Disconnect error"))
        manager = LifespanManager(mock_database, None, mock_build_middleware)

        messages: list[dict[str, Any]] = [
            {"type": "lifespan.startup"},
            {"type": "lifespan.shutdown"},
        ]
        sent: list[MutableMapping[str, Any]] = []

        async def receive() -> dict[str, Any]:
            return messages.pop(0)

        async def send(message: MutableMapping[str, Any]) -> None:
            sent.append(message)

        await manager.handle_lifespan({}, receive, send)

        # Should still send shutdown.complete despite error
        assert {"type": "lifespan.shutdown.complete"} in sent


class TestProperties(TestLifespanManager):
    """Tests for LifespanManager properties."""

    def test_started_initial_false(self, mock_build_middleware: MagicMock) -> None:
        """Should have started=False initially."""
        manager = LifespanManager(None, None, mock_build_middleware)
        assert manager.started is False

    def test_app_initial_none(self, mock_build_middleware: MagicMock) -> None:
        """Should have app=None initially."""
        manager = LifespanManager(None, None, mock_build_middleware)
        assert manager.app is None

    @pytest.mark.asyncio
    async def test_app_after_startup(self, mock_build_middleware: MagicMock) -> None:
        """Should have app set after startup."""
        manager = LifespanManager(None, None, mock_build_middleware)
        await manager.startup()
        assert manager.app is not None
        assert manager.app == mock_build_middleware.return_value
