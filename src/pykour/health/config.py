"""Health check configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Coroutine

if TYPE_CHECKING:
    from pykour.health.types import HealthStatus


# Type alias for health check functions
HealthCheckFunc = Callable[[], Coroutine[Any, Any, "HealthStatus"]]


@dataclass
class HealthCheckConfig:
    """Configuration for health check endpoint.

    Attributes:
        health_url: URL path for the health check endpoint.
                    Set to None to disable the health check endpoint.
        include_details: If True, include detailed check results and metadata.
        checks: List of custom health check functions to run.
        version: Application version to include in response.

    Example:
        # Basic configuration
        config = HealthCheckConfig()

        # With detailed output
        config = HealthCheckConfig(include_details=True)

        # With custom checks
        async def check_database() -> HealthStatus:
            return HealthStatus(name="database", status="healthy")

        config = HealthCheckConfig(
            include_details=True,
            checks=[check_database],
        )
    """

    health_url: str | None = "/health"
    include_details: bool = False
    checks: list[HealthCheckFunc] = field(default_factory=list)
    version: str | None = None
