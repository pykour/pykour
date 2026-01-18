"""ASGI lifespan management for Pykour application."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from pykour.cache.storage import CacheStorage
    from pykour.db import Database
    from pykour.types import Receive, Scope, Send


class LifespanManager:
    """Manages ASGI lifespan events (startup and shutdown).

    This class handles:
    - Application startup with database and cache connections
    - Application shutdown with resource cleanup
    - Thread-safe startup using double-checked locking
    - ASGI lifespan protocol handling
    """

    def __init__(
        self,
        database: "Database | None",
        cache: "CacheStorage | None",
        build_middleware: Callable[[], Any],
    ) -> None:
        """Initialize lifespan manager.

        Args:
            database: Optional database instance to connect/disconnect.
            cache: Optional cache storage to connect/disconnect.
            build_middleware: Callback to build middleware stack during startup.
        """
        self._database = database
        self._cache = cache
        self._build_middleware = build_middleware
        self._started = False
        self._startup_lock = asyncio.Lock()
        self._app: Any = None

    @property
    def started(self) -> bool:
        """Check if the application has been started."""
        return self._started

    @property
    def app(self) -> Any:
        """Get the built middleware stack application."""
        return self._app

    async def startup(self) -> Any:
        """Perform startup tasks.

        This method is thread-safe and uses double-checked locking to prevent
        race conditions when multiple concurrent requests trigger auto-start.

        Returns:
            The built middleware stack application.
        """
        # Fast path: already started
        if self._started:
            return self._app

        async with self._startup_lock:
            # Re-check after acquiring lock (double-checked locking)
            if self._started:
                return self._app

            # Build middleware stack during startup for thread safety
            if self._app is None:
                self._app = self._build_middleware()

            # Connect database
            if self._database is not None:
                await self._database.connect()

            # Connect cache
            if self._cache is not None:
                await self._cache.connect()

            self._started = True
            return self._app

    async def shutdown(self) -> None:
        """Perform shutdown tasks.

        Disconnects database and cache connections if they were established.
        """
        if not self._started:
            return

        # Disconnect database
        if self._database is not None:
            await self._database.disconnect()

        # Disconnect cache
        if self._cache is not None:
            await self._cache.disconnect()

        self._started = False

    async def handle_lifespan(
        self,
        scope: "Scope",
        receive: "Receive",
        send: "Send",
    ) -> None:
        """Handle ASGI lifespan protocol events.

        Args:
            scope: ASGI lifespan scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        while True:
            message = await receive()

            if message["type"] == "lifespan.startup":
                try:
                    await self.startup()
                    await send({"type": "lifespan.startup.complete"})
                except Exception as e:
                    await send({"type": "lifespan.startup.failed", "message": str(e)})
                    return

            elif message["type"] == "lifespan.shutdown":
                try:
                    await self.shutdown()
                    await send({"type": "lifespan.shutdown.complete"})
                except Exception:
                    # Always send shutdown.complete even on error
                    await send({"type": "lifespan.shutdown.complete"})
                return
