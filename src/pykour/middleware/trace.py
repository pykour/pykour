"""Trace middleware for request tracing.

This module provides middleware for extracting or generating trace IDs
to correlate logs across a single request lifecycle.

Example:
    from pykour import Pykour
    from pykour.middleware import TraceMiddleware, LoggingMiddleware

    app = Pykour()
    app.add_middleware(TraceMiddleware)      # First: sets trace_id
    app.add_middleware(LoggingMiddleware)    # Second: uses trace_id
"""

from __future__ import annotations

import re
from typing import Any

from pykour.logging.context import generate_trace_id, reset_trace_id, set_trace_id
from pykour.middleware.base import BaseMiddleware
from pykour.types import Receive, Scope, Send

# W3C traceparent format: version-trace_id-parent_id-flags
# Example: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
TRACEPARENT_REGEX = re.compile(
    r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$"
)


class TraceMiddleware(BaseMiddleware):
    """Request tracing middleware.

    Extracts or generates trace IDs for request correlation.
    The trace ID is made available via:
    - `pykour.logging.get_trace_id()` function
    - `scope["trace_id"]` in ASGI scope
    - Response header (default: X-Trace-ID)

    Header priority (first match wins):
        1. traceparent (W3C Trace Context) - extracts trace-id part
        2. X-Request-ID
        3. X-Trace-ID
        4. X-Correlation-ID
        5. Generate UUID v4 if no header found

    Example:
        from pykour import Pykour
        from pykour.middleware import TraceMiddleware

        app = Pykour()
        app.add_middleware(TraceMiddleware)

        # Custom response header
        app.add_middleware(TraceMiddleware, response_header="X-Request-ID")

    Attributes:
        response_header: The header name used in responses.
    """

    # Header names to check (in priority order)
    # Format: (header_name_bytes, needs_parsing)
    HEADER_PRIORITY: list[tuple[bytes, bool]] = [
        (b"traceparent", True),  # W3C format, needs parsing
        (b"x-request-id", False),
        (b"x-trace-id", False),
        (b"x-correlation-id", False),
    ]

    def __init__(
        self,
        app: Any,
        *,
        response_header: str = "X-Trace-ID",
    ) -> None:
        """Initialize trace middleware.

        Args:
            app: ASGI application to wrap.
            response_header: Header name for trace ID in response.
        """
        super().__init__(app)
        self.response_header = response_header
        self._response_header_bytes = response_header.lower().encode("latin-1")

    def _extract_trace_id(self, scope: Scope) -> str:
        """Extract trace ID from headers or generate a new one.

        Args:
            scope: ASGI scope containing headers.

        Returns:
            The extracted or generated trace ID.
        """
        headers = {key: value for key, value in scope.get("headers", [])}

        for header_name, needs_parse in self.HEADER_PRIORITY:
            if header_name in headers:
                value = headers[header_name].decode("latin-1")
                if needs_parse:
                    # W3C traceparent format
                    trace_id = self._parse_traceparent(value)
                    if trace_id:
                        return trace_id
                else:
                    stripped = value.strip()
                    if stripped:
                        return stripped

        # No valid header found: generate UUID
        return generate_trace_id()

    def _parse_traceparent(self, value: str) -> str | None:
        """Parse W3C traceparent header and extract trace-id.

        Args:
            value: The traceparent header value.

        Returns:
            The trace-id part, or None if parsing fails.

        Example:
            Input: "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
            Output: "4bf92f3577b34da6a3ce929d0e0e4736"
        """
        match = TRACEPARENT_REGEX.match(value.strip().lower())
        if match:
            return match.group(2)  # trace-id part
        return None

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request with trace ID.

        Args:
            scope: ASGI scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        trace_id = self._extract_trace_id(scope)
        set_trace_id(trace_id)

        # Also store in scope for other middleware
        scope["trace_id"] = trace_id

        async def send_wrapper(message: dict[str, Any]) -> None:
            """Wrap send to add trace ID to response headers."""
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append(
                    (self._response_header_bytes, trace_id.encode("latin-1"))
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            reset_trace_id()
