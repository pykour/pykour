from typing import Callable, List

from pykour.app import ASGIApp
from pykour.guid import GUID
from pykour.types import Receive, Scope, Send


class AppCallable:

    def __init__(self):
        self._app = None
        self._base_app = None
        self._middlewares: List[tuple[Callable, dict]] = []

    @property
    def app(self) -> ASGIApp:
        return self._base_app

    @app.setter
    def app(self, app: ASGIApp) -> None:
        self._base_app = app
        self._build_app()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self._app
        scope["guid"] = GUID.generate()
        await self._app(scope, receive, send)

    def add_middleware(self, middleware: Callable, **kwargs: dict) -> None:
        self._middlewares.append((middleware, kwargs))
        self._build_app()

    def _build_app(self) -> None:
        self._app = self._base_app
        for middleware, kwargs in self._middlewares:
            self._app = middleware(self._app, **kwargs)
