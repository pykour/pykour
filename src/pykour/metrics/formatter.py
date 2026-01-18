"""Prometheus metrics formatter."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pykour.metrics.collector import HistogramData


class PrometheusFormatter:
    """Prometheus text format (text/plain; version=0.0.4) formatter.

    Formats metrics into Prometheus exposition format:
    https://prometheus.io/docs/instrumenting/exposition_formats/

    Example:
        formatter = PrometheusFormatter(namespace="myapp", subsystem="http")
        output = formatter.format(metrics)
        # Output:
        # # HELP myapp_http_requests_total Total number of HTTP requests
        # # TYPE myapp_http_requests_total counter
        # myapp_http_requests_total{method="GET",path="/api",status="200"} 10
    """

    CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8"

    def __init__(self, namespace: str = "", subsystem: str = "http") -> None:
        """Initialize formatter.

        Args:
            namespace: Metric name prefix (e.g., "myapp").
            subsystem: Subsystem name (e.g., "http").
        """
        self._namespace = namespace
        self._subsystem = subsystem

    def _metric_name(self, name: str) -> str:
        """Build full metric name with namespace and subsystem.

        Args:
            name: Base metric name.

        Returns:
            Full metric name.
        """
        parts = []
        if self._namespace:
            parts.append(self._namespace)
        if self._subsystem:
            parts.append(self._subsystem)
        parts.append(name)
        return "_".join(parts)

    def _escape_label_value(self, value: str) -> str:
        """Escape label value for Prometheus format.

        Escapes backslash, double quote, and newline characters.

        Args:
            value: Label value to escape.

        Returns:
            Escaped label value.
        """
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def _format_labels(self, labels: dict[str, str]) -> str:
        """Format labels as {key="value",...}.

        Args:
            labels: Label key-value pairs.

        Returns:
            Formatted labels string.
        """
        if not labels:
            return ""
        pairs = [
            f'{k}="{self._escape_label_value(v)}"' for k, v in sorted(labels.items())
        ]
        return "{" + ",".join(pairs) + "}"

    def format(self, metrics: dict) -> str:
        """Format metrics into Prometheus text format.

        Args:
            metrics: Metrics data from MetricsCollector.collect().

        Returns:
            Prometheus formatted metrics string.
        """
        lines: list[str] = []

        # http_requests_total (Counter)
        self._format_counter(
            lines,
            "requests_total",
            "Total number of HTTP requests",
            metrics.get("requests_total", {}),
            label_names=["method", "path", "status"],
        )

        # http_request_duration_seconds (Histogram)
        self._format_histogram(
            lines,
            "request_duration_seconds",
            "HTTP request latency in seconds",
            metrics.get("request_duration", {}),
        )

        # http_requests_in_progress (Gauge)
        self._format_gauge(
            lines,
            "requests_in_progress",
            "Number of HTTP requests currently being processed",
            metrics.get("requests_in_progress", {}),
        )

        # http_response_size_bytes_total (Counter)
        self._format_counter(
            lines,
            "response_size_bytes_total",
            "Total size of HTTP responses in bytes",
            metrics.get("response_size_total", {}),
            label_names=["method", "path"],
        )

        return "\n".join(lines) + "\n" if lines else ""

    def _format_counter(
        self,
        lines: list[str],
        name: str,
        help_text: str,
        data: dict,
        label_names: list[str],
    ) -> None:
        """Format counter metric.

        Args:
            lines: Output lines list.
            name: Metric base name.
            help_text: HELP text.
            data: Counter data (key tuple -> count).
            label_names: Label names for the key tuple.
        """
        if not data:
            return

        full_name = self._metric_name(name)
        lines.append(f"# HELP {full_name} {help_text}")
        lines.append(f"# TYPE {full_name} counter")

        for key, count in sorted(data.items()):
            labels = dict(zip(label_names, key, strict=True))
            label_str = self._format_labels(labels)
            lines.append(f"{full_name}{label_str} {count}")

    def _format_gauge(
        self,
        lines: list[str],
        name: str,
        help_text: str,
        data: dict[tuple[str, str], int],
    ) -> None:
        """Format gauge metric.

        Args:
            lines: Output lines list.
            name: Metric base name.
            help_text: HELP text.
            data: Gauge data ((method, path) -> value).
        """
        if not data:
            return

        full_name = self._metric_name(name)
        lines.append(f"# HELP {full_name} {help_text}")
        lines.append(f"# TYPE {full_name} gauge")

        for (method, path), value in sorted(data.items()):
            labels = self._format_labels({"method": method, "path": path})
            lines.append(f"{full_name}{labels} {value}")

    def _format_histogram(
        self,
        lines: list[str],
        name: str,
        help_text: str,
        data: dict[tuple[str, str], HistogramData],
    ) -> None:
        """Format histogram metric.

        Args:
            lines: Output lines list.
            name: Metric base name.
            help_text: HELP text.
            data: Histogram data ((method, path) -> HistogramData).
        """
        if not data:
            return

        full_name = self._metric_name(name)
        lines.append(f"# HELP {full_name} {help_text}")
        lines.append(f"# TYPE {full_name} histogram")

        for (method, path), hist_data in sorted(data.items()):
            base_labels = {"method": method, "path": path}

            # Buckets (cumulative)
            cumulative = 0
            for bucket in sorted(hist_data.buckets.keys()):
                cumulative += hist_data.buckets[bucket]
                labels = self._format_labels({**base_labels, "le": str(bucket)})
                lines.append(f"{full_name}_bucket{labels} {cumulative}")

            # +Inf bucket
            labels = self._format_labels({**base_labels, "le": "+Inf"})
            lines.append(f"{full_name}_bucket{labels} {hist_data.count}")

            # sum and count
            labels = self._format_labels(base_labels)
            lines.append(f"{full_name}_sum{labels} {hist_data.sum}")
            lines.append(f"{full_name}_count{labels} {hist_data.count}")
