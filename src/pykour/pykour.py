import logging
import os
from typing import Callable, Any

from pykour.app import ASGIApp
from pykour.config import Config
from pykour.db.pool import ConnectionPool
from pykour.logging import setup_logging

from pykour.router import Router
from pykour.types import Scope, Receive, Send


class Pykour(Router):
    """Pykour application."""

    def __init__(self, prefix="/", config: Config = Config()) -> None:
        """Initialize Pykour application.

        Args:
            prefix: URL prefix. Default is "/".
            config: Configuration instance.
        """

        super().__init__(prefix=prefix)
        self.production_mode = os.getenv("PYKOUR_ENV") == "production"
        self._config = config
        setup_logging(self._config.get_log_levels())
        self._logger = logging.getLogger("pykour")

        self.app = ASGIApp()

        self.pool = None
        if self._config.get_datasource_type():
            self.pool = ConnectionPool(self._config)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
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

        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(f"Add middleware: {middleware.__name__}")
        self.app = middleware(self.app, **kwargs)
