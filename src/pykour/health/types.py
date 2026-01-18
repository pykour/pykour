"""Health check types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HealthStatus:
    """Status of a single health check.

    Attributes:
        name: Name of the health check (e.g., "database", "cache").
        status: Current status ("healthy", "unhealthy", "degraded").
        latency_ms: Optional latency of the check in milliseconds.
        error: Optional error message if the check failed.
        details: Optional additional details about the check.

    Example:
        # Healthy check
        status = HealthStatus(name="database", status="healthy", latency_ms=5)

        # Unhealthy check with error
        status = HealthStatus(
            name="cache",
            status="unhealthy",
            error="Connection timeout",
        )
    """

    name: str
    status: str  # "healthy", "unhealthy", "degraded"
    latency_ms: float | None = None
    error: str | None = None
    details: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for JSON serialization."""
        result: dict[str, object] = {
            "name": self.name,
            "status": self.status,
        }
        if self.latency_ms is not None:
            result["latency_ms"] = self.latency_ms
        if self.error is not None:
            result["error"] = self.error
        if self.details is not None:
            result["details"] = self.details
        return result
