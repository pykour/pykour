"""Request size limit middleware for Pykour."""

from __future__ import annotations

from typing import Any, Sequence

from pykour.middleware.base import BaseMiddleware
from pykour.middleware.utils import extract_header
from pykour.response import JSONResponse
from pykour.types import Message, Receive, Scope, Send

# Default max size: 1MB
DEFAULT_MAX_SIZE = 1 * 1024 * 1024  # 1MB = 1048576 bytes


class RequestTooLargeError(Exception):
    """Raised when request body exceeds size limit."""

    def __init__(self, max_size: int) -> None:
        self.max_size = max_size
        super().__init__(f"Request body exceeds {max_size} bytes")


class RequestSizeLimitMiddleware(BaseMiddleware):
    """Middleware that limits the size of incoming request bodies.

    Protects against memory exhaustion attacks by rejecting requests
    that exceed the configured size limit.

    Example:
        # Basic usage (1MB default)
        app.add_middleware(RequestSizeLimitMiddleware)

        # Custom limit
        app.add_middleware(
            RequestSizeLimitMiddleware,
            max_size=10 * 1024 * 1024,  # 10MB
        )

        # Different limits by content type
        app.add_middleware(
            RequestSizeLimitMiddleware,
            max_size=1 * 1024 * 1024,  # 1MB default
            max_size_by_content_type={
                "multipart/form-data": 50 * 1024 * 1024,  # 50MB for uploads
                "application/json": 1 * 1024 * 1024,  # 1MB for JSON
            },
        )
    """

    def __init__(
        self,
        app: Any,
        *,
        max_size: int = DEFAULT_MAX_SIZE,
        max_size_by_content_type: dict[str, int] | None = None,
        exclude_paths: Sequence[str] = (),
        check_content_length: bool = True,
        check_body_size: bool = True,
    ) -> None:
        """Initialize request size limit middleware.

        Args:
            app: The ASGI application to wrap.
            max_size: Maximum request body size in bytes.
            max_size_by_content_type: Content-Type specific size limits.
            exclude_paths: Paths to exclude from size checking.
            check_content_length: Check Content-Length header upfront.
            check_body_size: Check actual body size during streaming.
        """
        super().__init__(app)
        self.max_size = max_size
        self.max_size_by_content_type = max_size_by_content_type or {}
        self.exclude_paths = list(exclude_paths)
        self.check_content_length = check_content_length
        self.check_body_size = check_body_size

    def _get_content_length(self, scope: Scope) -> int:
        """Extract Content-Length header value."""
        content_length = extract_header(scope, b"content-length")
        if content_length:
            try:
                return int(content_length)
            except ValueError:
                pass
        return 0

    def _get_max_size(self, scope: Scope) -> int:
        """Get max size for request based on Content-Type."""
        if not self.max_size_by_content_type:
            return self.max_size

        # Extract Content-Type header
        content_type = extract_header(scope, b"content-type")
        if content_type:
            # Extract base content type (without parameters like charset)
            base_type = content_type.split(";")[0].strip().lower()
            if base_type in self.max_size_by_content_type:
                return self.max_size_by_content_type[base_type]

        return self.max_size

    def _payload_too_large_response(self, max_size: int) -> JSONResponse:
        """Create 413 Payload Too Large response."""
        return JSONResponse(
            {
                "error": "Payload Too Large",
                "detail": f"Request body exceeds the maximum allowed size of {max_size} bytes",
                "max_size": max_size,
            },
            status_code=413,
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request with size limiting."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")

        # Skip size check for excluded paths
        if not self.should_process_path(path, self.exclude_paths):
            await self.app(scope, receive, send)
            return

        max_size = self._get_max_size(scope)

        # Check Content-Length header first (fast rejection)
        if self.check_content_length:
            content_length = self._get_content_length(scope)
            if content_length > max_size:
                response = self._payload_too_large_response(max_size)
                await response(scope, receive, send)
                return

        # If body size checking is disabled, pass through
        if not self.check_body_size:
            await self.app(scope, receive, send)
            return

        # Wrap receive to track body size during streaming
        body_size = 0

        async def receive_with_limit() -> Message:
            nonlocal body_size

            message = await receive()

            if message["type"] == "http.request":
                body = message.get("body", b"")
                body_size += len(body)

                if body_size > max_size:
                    raise RequestTooLargeError(max_size)

            return message

        try:
            await self.app(scope, receive_with_limit, send)
        except RequestTooLargeError as e:
            response = self._payload_too_large_response(e.max_size)
            await response(scope, receive, send)
