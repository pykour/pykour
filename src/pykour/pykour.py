from .types import Scope, Receive, Send
from .app import ASGIApp


class Pykour:
    def __init__(self) -> None:
        self.app = ASGIApp()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)
