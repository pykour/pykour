"""Prometheus metrics configuration."""

from dataclasses import dataclass, field


@dataclass
class MetricsConfig:
    """Configuration for Prometheus metrics endpoint.

    Attributes:
        metrics_url: URL path for the metrics endpoint.
                     Set to None to disable the metrics endpoint.
        exclude_paths: Paths to exclude from metrics collection.
        latency_buckets: Histogram bucket boundaries for latency (seconds).
        normalize_paths: Whether to normalize paths to reduce cardinality.
        namespace: Prefix for metric names (e.g., "myapp").
        subsystem: Subsystem name for metric names (e.g., "http").
    """

    metrics_url: str | None = "/metrics"

    exclude_paths: list[str] = field(default_factory=lambda: ["/health", "/metrics"])

    latency_buckets: tuple[float, ...] = (
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
    )

    normalize_paths: bool = True

    namespace: str = ""

    subsystem: str = "http"
