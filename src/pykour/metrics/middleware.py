"""Prometheus metrics collection middleware."""

from __future__ import annotations

import time
from typing import Any

from pykour.metrics.collector import MetricsCollector
from pykour.metrics.config import MetricsConfig
from pykour.middleware.base import BaseMiddleware
from pykour.middleware.utils import is_path_excluded
from pykour.types import Receive, Scope, Send


class MetricsMiddleware(BaseMiddleware):
    """Request/Response metrics collection middleware.

    Collects HTTP request metrics for Prometheus:
    - Total request count (by method, path, status)
    - Request duration histogram
    - In-progress request gauge
    - Response size counter

    Example:
        from pykour.metrics import MetricsConfig, MetricsCollector, MetricsMiddleware

        config = MetricsConfig()
        collector = MetricsCollector(buckets=config.latency_buckets)

        app.add_middleware(
            MetricsMiddleware,
            collector=collector,
            config=config,
        )
    """

    def __init__(
        self,
        app: Any,
        *,
        collector: MetricsCollector,
        config: MetricsConfig,
    ) -> None:
        """Initialize metrics middleware.

        Args:
            app: The ASGI application to wrap.
            collector: Metrics collector instance.
            config: Metrics configuration.
        """
        super().__init__(app)
        self._collector = collector
        self._config = config

    def _normalize_path(self, scope: Scope) -> str:
        """Normalize path to reduce label cardinality.

        Uses path_pattern from scope if available (set by router),
        falling back to the actual path.

        Args:
            scope: ASGI scope.

        Returns:
            Normalized path.
        """
        path = scope.get("path", "/")

        if not self._config.normalize_paths:
            return path

        # Use path_pattern if set by router (e.g., /users/{id})
        path_pattern = scope.get("path_pattern")
        if path_pattern:
            return path_pattern

        return path

    def _is_excluded(self, path: str) -> bool:
        """Check if path is excluded from metrics collection.

        Args:
            path: Request path.

        Returns:
            True if path should be excluded.
        """
        return is_path_excluded(path, self._config.exclude_paths)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request with metrics collection."""
        # Non-HTTP requests pass through without metrics
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")

        # Skip excluded paths
        if self._is_excluded(path):
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        normalized_path = self._normalize_path(scope)

        # Record start time and increment in-progress
        start_time = time.perf_counter()
        self._collector.inc_in_progress(method, normalized_path)

        # Capture response status and size
        status_code = 500
        response_size = 0

        async def send_wrapper(message: dict[str, Any]) -> None:
            nonlocal status_code, response_size
            if message["type"] == "http.response.start":
                status_code = message.get("status", 500)
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                if body:
                    response_size += len(body)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            # Calculate duration
            duration = time.perf_counter() - start_time

            # Record metrics
            self._collector.dec_in_progress(method, normalized_path)
            self._collector.inc_requests_total(
                method, normalized_path, str(status_code)
            )
            self._collector.observe_duration(method, normalized_path, duration)
            self._collector.add_response_size(method, normalized_path, response_size)
