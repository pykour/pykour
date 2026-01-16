"""Logging middleware for Pykour."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Literal, Sequence

from pykour import json as pykour_json
from pykour.middleware.base import BaseMiddleware
from pykour.middleware.utils import (
    SENSITIVE_HEADERS,
    get_client_ip,
    get_content_length,
    get_user_agent,
    is_path_excluded,
)
from pykour.types import Receive, Scope, Send


class LoggingMiddleware(BaseMiddleware):
    """Request/Response logging middleware.

    Logs HTTP requests and responses with configurable format and level.
    Automatically adjusts log level based on response status code:
    - 1xx-3xx: INFO
    - 4xx: WARNING
    - 5xx: ERROR

    Example:
        # Basic usage
        app.add_middleware(LoggingMiddleware)

        # Custom configuration
        app.add_middleware(
            LoggingMiddleware,
            logger_name="myapp.access",
            level="DEBUG",
            exclude_paths=["/health", "/metrics"],
            log_request_headers=True,
        )

        # JSON format for production
        app.add_middleware(
            LoggingMiddleware,
            format="json",
        )

    Log output formats:
        Text: 127.0.0.1 - "GET /api/users" 200 12.5ms
        JSON: {"type": "access", "trace_id": "...", "method": "GET", ...}
    """

    def __init__(
        self,
        app: Any,
        *,
        logger_name: str = "pykour.access",
        level: str | int = "INFO",
        exclude_paths: Sequence[str] = (),
        log_request_headers: bool = False,
        log_response_headers: bool = False,
        format: Literal["text", "json"] = "text",
    ) -> None:
        """Initialize logging middleware.

        Args:
            app: The ASGI application to wrap.
            logger_name: Name of the logger to use.
            level: Minimum log level (string or int).
            exclude_paths: List of paths to exclude from logging.
            log_request_headers: Whether to include request headers in logs.
            log_response_headers: Whether to include response headers in logs.
            format: Output format ("text" or "json").
        """
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)
        self.level = self._parse_level(level)
        self.exclude_paths = list(exclude_paths)
        self.log_request_headers = log_request_headers
        self.log_response_headers = log_response_headers
        self.format = format

    def _parse_level(self, level: str | int) -> int:
        """Parse log level string to int."""
        if isinstance(level, int):
            return level
        return getattr(logging, level.upper(), logging.INFO)

    def _is_excluded(self, path: str) -> bool:
        """Check if path is excluded from logging."""
        return is_path_excluded(path, self.exclude_paths)

    def _get_client_ip(self, scope: Scope) -> str:
        """Extract client IP from scope."""
        return get_client_ip(scope)

    def _get_user_agent(self, scope: Scope) -> str:
        """Extract User-Agent header from scope."""
        return get_user_agent(scope)

    def _get_content_length(self, scope: Scope) -> int:
        """Extract Content-Length from request headers."""
        return get_content_length(scope)

    def _get_status_level(self, status_code: int) -> int:
        """Get log level based on status code.

        Returns:
            INFO for 1xx-3xx, WARNING for 4xx, ERROR for 5xx.
        """
        if status_code >= 500:
            return logging.ERROR
        elif status_code >= 400:
            return logging.WARNING
        return logging.INFO

    def _format_headers(self, headers: list[tuple[bytes, bytes]]) -> str:
        """Format headers for logging with sensitive values masked."""
        formatted = []
        for key, value in headers:
            key_str = key.decode("latin-1")
            # Mask sensitive headers using centralized list
            if key_str.lower() in SENSITIVE_HEADERS:
                formatted.append(f"{key_str}: [REDACTED]")
            else:
                formatted.append(f"{key_str}: {value.decode('latin-1')}")
        return ", ".join(formatted)

    def _log_request_text(
        self,
        scope: Scope,
        status_code: int,
        duration_ms: float,
        response_headers: list[tuple[bytes, bytes]] | None = None,
        response_size: int = 0,
    ) -> None:
        """Log the request/response in text format."""
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"")
        client_ip = self._get_client_ip(scope)

        # Build full path with query string
        full_path = path
        if query_string:
            full_path = f"{path}?{query_string.decode('latin-1')}"

        level = self._get_status_level(status_code)

        # Build log message
        message = (
            f'{client_ip} - "{method} {full_path}" {status_code} {duration_ms:.1f}ms'
        )

        # Add request headers if enabled
        if self.log_request_headers:
            request_headers = scope.get("headers", [])
            if request_headers:
                message += f" | Request: {self._format_headers(request_headers)}"

        # Add response headers if enabled
        if self.log_response_headers and response_headers:
            message += f" | Response: {self._format_headers(response_headers)}"

        self.logger.log(level, message)

    def _log_request_json(
        self,
        scope: Scope,
        status_code: int,
        duration_ms: float,
        response_headers: list[tuple[bytes, bytes]] | None = None,
        response_size: int = 0,
    ) -> None:
        """Log the request/response in JSON format."""
        from pykour.logging.context import get_trace_id

        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        query_string = scope.get("query_string", b"").decode("latin-1")

        log_data: dict[str, Any] = {
            "type": "access",
            "trace_id": get_trace_id() or scope.get("trace_id", "-"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "path": path,
            "query_string": query_string,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 3),
            "client_ip": self._get_client_ip(scope),
            "user_agent": self._get_user_agent(scope),
            "request_size": self._get_content_length(scope),
            "response_size": response_size,
        }

        # Add request headers if enabled
        if self.log_request_headers:
            request_headers = scope.get("headers", [])
            if request_headers:
                log_data["request_headers"] = self._format_headers(request_headers)

        # Add response headers if enabled
        if self.log_response_headers and response_headers:
            log_data["response_headers"] = self._format_headers(response_headers)

        level = self._get_status_level(status_code)
        self.logger.log(level, pykour_json.dumps(log_data).decode("utf-8"))

    def _log_request(
        self,
        scope: Scope,
        status_code: int,
        duration_ms: float,
        response_headers: list[tuple[bytes, bytes]] | None = None,
        response_size: int = 0,
    ) -> None:
        """Log the request/response based on configured format."""
        if self.format == "json":
            self._log_request_json(
                scope, status_code, duration_ms, response_headers, response_size
            )
        else:
            self._log_request_text(
                scope, status_code, duration_ms, response_headers, response_size
            )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request with logging."""
        # Non-HTTP requests pass through without logging
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")

        # Skip excluded paths
        if self._is_excluded(path):
            await self.app(scope, receive, send)
            return

        # Record start time
        start_time = time.perf_counter()

        # Capture response status, headers, and size
        status_code = 500
        response_headers: list[tuple[bytes, bytes]] | None = None
        response_size = 0

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code, response_headers, response_size
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
                if self.log_response_headers or self.format == "json":
                    response_headers = message.get("headers", [])
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    response_size += len(body)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log request/response
            self._log_request(
                scope, status_code, duration_ms, response_headers, response_size
            )
