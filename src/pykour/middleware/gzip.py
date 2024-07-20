import gzip
import io
from typing import Callable, Union, List, Dict

from pykour.types import ASGIApp, Scope, Receive, Send
from pykour.middleware.base import BaseMiddleware


class GZipMiddleware(BaseMiddleware):
    """Middleware to GZIP responses."""

    def __init__(self, app: ASGIApp, minimum_size: int = 500):
        """
        Initialize the middleware with the application.

        Args:
            app: The ASGI application.
            minimum_size: The minimum size in bytes for responses to be gzipped.
        """
        super().__init__(app)
        self.minimum_size = minimum_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """
        Call the middleware.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive channel.
            send: The ASGI send channel.
        """
        if scope["type"] == "http":
            headers = {k.lower(): v for k, v in scope["headers"]}
            if b"accept-encoding" in headers and b"gzip" in headers[b"accept-encoding"]:
                responder = GZipResponder(self.app, self.minimum_size)
                await responder(scope, receive, send)
            else:
                await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class GZipResponder:
    def __init__(self, app: ASGIApp, minimum_size: int):
        self.app = app
        self.minimum_size = minimum_size
        self.body: List[bytes] = []
        self.send: Union[Callable, None] = None
        self.initial_message: Union[Dict, None] = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        self.send = send
        self.body = []
        self.initial_message = None

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                self.initial_message = message
            elif message["type"] == "http.response.body":
                self.body.append(message.get("body", b""))
                if not message.get("more_body", False):
                    body = b"".join(self.body)
                    if len(body) >= self.minimum_size:
                        gzip_buffer = io.BytesIO()
                        with gzip.GzipFile(fileobj=gzip_buffer, mode="wb") as f:
                            f.write(body)
                        body = gzip_buffer.getvalue()
                        self.initial_message["headers"].append((b"content-encoding", b"gzip"))
                    await self.send(self.initial_message)
                    await self.send({"type": "http.response.body", "body": body, "more_body": False})
            else:
                await self.send(message)

        await self.app(scope, receive, send_wrapper)


def gzip_middleware(minimum_size: int = 500):
    def middleware(app: ASGIApp):
        return GZipMiddleware(app, minimum_size=minimum_size)

    return middleware
