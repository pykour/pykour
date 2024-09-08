import os
from typing import Callable, Any, Optional
from uuid import uuid4

from pykour.app import ASGIApp
from pykour.config import Config
from pykour.db.pool import ConnectionPool
from pykour.globals import thread_local
from pykour.logging import setup_logging, write_debug_log

from pykour.router import Router
from pykour.types import Scope, Receive, Send


class Pykour(Router):
    """Pykour application."""

    def __init__(
        self,
        title: str = "Pykour",
        summary: Optional[str] = None,
        description: str = "",
        version: str = "0.1.0",
        prefix="/",
        config: Config = Config(),
    ) -> None:
        """Initialize Pykour application.

        Args:
            prefix: URL prefix. Default is "/".
            config: Configuration instance.
        """
        self.production_mode = os.getenv("PYKOUR_ENV") == "production"
        self.title = title
        self.summary = summary
        self.description = description
        self.version = version

        super().__init__(prefix=prefix)
        self._config = config
        setup_logging(self._config.get_log_levels())

        self.app = ASGIApp()

        self.pool = None
        if self._config.get_datasource_type():
            self.pool = ConnectionPool(self._config)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        thread_local.request_id = str(uuid4())
        await self.app(scope, receive, send)

    @property
    def config(self) -> Config:
        """Get the configuration.

        Returns:
            Config instance.
        """

        return self._config

    def add_middleware(self, middleware: Callable, **kwargs: Any) -> None:
        """Add middleware to the application.

        Args:
            middleware: Middleware class.
            kwargs: Middleware arguments.
        """

        write_debug_log(f"Add middleware: {middleware.__name__}")
        self.app = middleware(self.app, **kwargs)
