"""Health check endpoint handler."""

from __future__ import annotations

import time
from typing import Any

from pykour.health.config import HealthCheckConfig
from pykour.health.types import HealthStatus
from pykour.response import JSONResponse
from pykour.types import Receive, Scope, Send


class HealthCheckHandler:
    """Handler for health check endpoint.

    This class handles requests to the health check endpoint,
    returning a JSON response indicating the application health status.
    Supports custom health checks and detailed status information.

    Example:
        # Basic usage
        config = HealthCheckConfig()
        handler = HealthCheckHandler(config)

        # With custom checks
        async def check_db() -> HealthStatus:
            return HealthStatus(name="database", status="healthy")

        config = HealthCheckConfig(
            include_details=True,
            checks=[check_db],
        )
        handler = HealthCheckHandler(config)
    """

    def __init__(self, config: HealthCheckConfig) -> None:
        """Initialize health check handler.

        Args:
            config: Health check configuration.
        """
        self._config = config
        self._start_time = time.time()

    def matches(self, path: str) -> bool:
        """Check if the path matches the health check endpoint.

        Args:
            path: Request path.

        Returns:
            True if path matches the health check endpoint.
        """
        return path == self._config.health_url

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> bool:
        """Handle health check request.

        Args:
            scope: ASGI scope.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            True if the request was handled, False otherwise.
        """
        path = scope.get("path", "/")
        method = scope.get("method", "GET")

        # Only handle GET requests for health check
        if method != "GET":
            return False

        if path == self._config.health_url:
            response_data = await self._build_response()
            # "ok" and "healthy" both mean healthy status
            is_healthy = response_data["status"] in ("ok", "healthy")
            status_code = 200 if is_healthy else 503
            response = JSONResponse(response_data, status_code=status_code)
            await response(scope, receive, send)
            return True

        return False

    async def _build_response(self) -> dict[str, Any]:
        """Build health check response data.

        Returns:
            Health check response dictionary.
        """
        # Run custom health checks
        check_results: list[HealthStatus] = []
        overall_status = "healthy"

        for check_func in self._config.checks:
            try:
                start = time.time()
                result = await check_func()
                # Add latency if not already set
                if result.latency_ms is None:
                    result.latency_ms = round((time.time() - start) * 1000, 2)
                check_results.append(result)

                # Update overall status based on individual check
                if result.status == "unhealthy":
                    overall_status = "unhealthy"
                elif result.status == "degraded" and overall_status == "healthy":
                    overall_status = "degraded"

            except Exception as e:
                # If a check raises an exception, mark it as unhealthy
                check_results.append(
                    HealthStatus(
                        name=getattr(check_func, "__name__", "unknown"),
                        status="unhealthy",
                        error=str(e),
                    )
                )
                overall_status = "unhealthy"

        # Build response
        if self._config.include_details:
            response: dict[str, Any] = {
                "status": overall_status,
            }

            if check_results:
                response["checks"] = [r.to_dict() for r in check_results]

            response["uptime_seconds"] = round(time.time() - self._start_time, 2)

            if self._config.version:
                response["version"] = self._config.version

            return response
        else:
            # Simple response for non-detailed mode
            return {"status": "ok" if overall_status == "healthy" else overall_status}

    def add_check(self, check_func: Any) -> None:
        """Add a health check function.

        Args:
            check_func: Async function that returns HealthStatus.

        Example:
            async def check_cache() -> HealthStatus:
                return HealthStatus(name="cache", status="healthy")

            handler.add_check(check_cache)
        """
        self._config.checks.append(check_func)


def setup_health_check(config: HealthCheckConfig) -> HealthCheckHandler:
    """Set up health check endpoint for a Pykour application.

    Args:
        config: Health check configuration.

    Returns:
        Health check handler instance.
    """
    return HealthCheckHandler(config)
