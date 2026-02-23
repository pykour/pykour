"""Middleware support for Pykour."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from pykour.middleware.utils import is_path_excluded
from pykour.types import MiddlewareFunc, Receive, Scope, Send

if TYPE_CHECKING:
    from pykour.request import Request
    from pykour.response import Response


class BaseMiddleware(ABC):
    """Base class for ASGI middleware.

    Example:
        class LoggingMiddleware(BaseMiddleware):
            async def __call__(
                self,
                scope: Scope,
                receive: Receive,
                send: Send,
            ) -> None:
                print(f"Request: {scope['path']}")
                await self.app(scope, receive, send)
                print("Response sent")

        app.add_middleware(LoggingMiddleware)
    """

    def __init__(self, app: Any, **options: Any) -> None:
        """Initialize middleware.

        Args:
            app: The ASGI application to wrap.
            **options: Additional options for the middleware.
        """
        self.app = app

    def should_process_path(self, path: str, exclude_paths: Sequence[str]) -> bool:
        """Return True if the middleware should process this path.

        Args:
            path: The request path to check.
            exclude_paths: List of paths/prefixes to exclude from processing.

        Returns:
            True if the path should be processed, False if it should be skipped.
        """
        return not is_path_excluded(path, exclude_paths)

    @abstractmethod
    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request.

        Args:
            scope: ASGI scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        ...


class _ResponseCapture:
    """Capture ASGI response for middleware call_next."""

    def __init__(self) -> None:
        self.status_code: int = 200
        self.headers: list[tuple[bytes, bytes]] = []
        self.body: bytes = b""
        self._body_parts: list[bytes] = []
        self._started = False
        self._finished = False
        self._finished_event = asyncio.Event()

    async def __call__(self, message: dict[str, Any]) -> None:
        """Capture ASGI messages."""
        if message["type"] == "http.response.start":
            self.status_code = message["status"]
            self.headers = list(message.get("headers", []))
            self._started = True
        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            if body:
                self._body_parts.append(body)
            if not message.get("more_body", False):
                self.body = b"".join(self._body_parts)
                self._finished = True
                self._finished_event.set()

    async def wait_for_response(self) -> None:
        """Wait for the response to complete."""
        await self._finished_event.wait()

    def mark_finished_on_error(self) -> None:
        """Mark the capture as finished due to an error.

        This ensures wait_for_response() unblocks even if the app
        raised an exception before sending a complete response.
        """
        if not self._finished:
            self._finished = True
            self._finished_event.set()

    def to_response(self) -> "Response":
        """Convert captured data to a Response object."""
        from pykour.response import Response

        # Convert headers from bytes to str, preserving duplicates
        headers: list[tuple[str, str]] = [
            (key.decode("latin-1"), value.decode("latin-1"))
            for key, value in self.headers
        ]

        return Response(
            content=self.body,
            status_code=self.status_code,
            headers=headers,
        )


class FunctionMiddleware(BaseMiddleware):
    """Wrapper for function-style middleware.

    Example:
        @app.middleware
        async def logging_middleware(request, call_next):
            print(f"Request: {request.method} {request.path}")
            response = await call_next(request)
            print(f"Response: {response.status_code}")
            return response
    """

    def __init__(
        self,
        app: Any,
        *,
        dispatch: MiddlewareFunc,
    ) -> None:
        """Initialize function middleware.

        Args:
            app: The ASGI application to wrap.
            dispatch: The middleware function.
        """
        super().__init__(app)
        self.dispatch = dispatch

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from pykour.request import Request

        # Create request object
        request = Request(scope, receive, scope.get("path_params", {}))

        async def call_next(req: Request) -> "Response":
            """Call the next middleware/app and return the response."""
            capture = _ResponseCapture()

            try:
                # Call the wrapped app with our capture send
                await self.app(req.scope, req.receive, capture)
            except Exception:
                # Ensure wait_for_response() unblocks even on error
                capture.mark_finished_on_error()
                raise
            await capture.wait_for_response()

            return capture.to_response()

        # Call the dispatch function
        response = await self.dispatch(request, call_next)

        # Send the response
        await response(scope, receive, send)
