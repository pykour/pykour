"""Prometheus metrics collector."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class HistogramData:
    """Histogram metric data.

    Attributes:
        buckets: Bucket upper bounds mapped to cumulative counts.
        sum: Sum of all observed values.
        count: Total number of observations.
    """

    buckets: dict[float, int] = field(default_factory=dict)
    sum: float = 0.0
    count: int = 0


class MetricsCollector:
    """Thread-safe Prometheus metrics collector.

    Collects the following metrics:
    - Counter: http_requests_total (method, path, status)
    - Histogram: http_request_duration_seconds (method, path)
    - Gauge: http_requests_in_progress (method, path)
    - Counter: http_response_size_bytes_total (method, path)

    Example:
        collector = MetricsCollector(buckets=(0.1, 0.5, 1.0))

        # Record a request
        collector.inc_in_progress("GET", "/api/users")
        # ... handle request ...
        collector.dec_in_progress("GET", "/api/users")
        collector.inc_requests_total("GET", "/api/users", "200")
        collector.observe_duration("GET", "/api/users", 0.05)
        collector.add_response_size("GET", "/api/users", 1024)

        # Get metrics snapshot
        metrics = collector.collect()
    """

    def __init__(self, buckets: tuple[float, ...]) -> None:
        """Initialize metrics collector.

        Args:
            buckets: Histogram bucket boundaries for latency (seconds).
        """
        self._lock = threading.Lock()
        self._buckets = buckets

        # Counter: http_requests_total{method, path, status}
        self._requests_total: dict[tuple[str, str, str], int] = {}

        # Histogram: http_request_duration_seconds{method, path}
        self._request_duration: dict[tuple[str, str], HistogramData] = {}

        # Gauge: http_requests_in_progress{method, path}
        self._requests_in_progress: dict[tuple[str, str], int] = {}

        # Counter: http_response_size_bytes_total{method, path}
        self._response_size_total: dict[tuple[str, str], int] = {}

    def inc_requests_total(self, method: str, path: str, status: str) -> None:
        """Increment total request count.

        Args:
            method: HTTP method (GET, POST, etc.).
            path: Request path.
            status: HTTP status code as string.
        """
        with self._lock:
            key = (method, path, status)
            self._requests_total[key] = self._requests_total.get(key, 0) + 1

    def observe_duration(self, method: str, path: str, duration: float) -> None:
        """Record request duration in histogram.

        Args:
            method: HTTP method.
            path: Request path.
            duration: Request duration in seconds.
        """
        with self._lock:
            key = (method, path)
            if key not in self._request_duration:
                self._request_duration[key] = HistogramData(
                    buckets={b: 0 for b in self._buckets}
                )

            data = self._request_duration[key]
            data.sum += duration
            data.count += 1

            # Increment bucket counts (non-cumulative, will be cumulated on format)
            for bucket in self._buckets:
                if duration <= bucket:
                    data.buckets[bucket] += 1
                    break

    def inc_in_progress(self, method: str, path: str) -> None:
        """Increment in-progress request count.

        Args:
            method: HTTP method.
            path: Request path.
        """
        with self._lock:
            key = (method, path)
            self._requests_in_progress[key] = self._requests_in_progress.get(key, 0) + 1

    def dec_in_progress(self, method: str, path: str) -> None:
        """Decrement in-progress request count.

        Args:
            method: HTTP method.
            path: Request path.
        """
        with self._lock:
            key = (method, path)
            current = self._requests_in_progress.get(key, 1)
            self._requests_in_progress[key] = max(0, current - 1)

    def add_response_size(self, method: str, path: str, size: int) -> None:
        """Add to total response size.

        Args:
            method: HTTP method.
            path: Request path.
            size: Response body size in bytes.
        """
        with self._lock:
            key = (method, path)
            self._response_size_total[key] = (
                self._response_size_total.get(key, 0) + size
            )

    def collect(self) -> dict[str, dict]:
        """Collect all metrics as a snapshot.

        Returns:
            Dictionary containing all metric data.
        """
        with self._lock:
            return {
                "requests_total": dict(self._requests_total),
                "request_duration": {
                    k: HistogramData(
                        buckets=dict(v.buckets),
                        sum=v.sum,
                        count=v.count,
                    )
                    for k, v in self._request_duration.items()
                },
                "requests_in_progress": dict(self._requests_in_progress),
                "response_size_total": dict(self._response_size_total),
            }
