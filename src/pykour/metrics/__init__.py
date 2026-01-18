"""Prometheus metrics module for Pykour.

This module provides Prometheus-compatible metrics collection and exposition:

- MetricsConfig: Configuration for metrics endpoint and collection.
- MetricsCollector: Thread-safe metrics collector.
- MetricsHandler: /metrics endpoint handler.
- MetricsMiddleware: Request metrics collection middleware.
- PrometheusFormatter: Prometheus text format formatter.

Example:
    from pykour import Pykour

    app = Pykour(routes_dir="routes", metrics_url="/metrics")
    app.enable_metrics()  # Enable metrics collection

    # Or with custom configuration:
    app = Pykour(routes_dir="routes", metrics_url="/prometheus/metrics")
    app.enable_metrics()
"""

from pykour.metrics.collector import HistogramData, MetricsCollector
from pykour.metrics.config import MetricsConfig
from pykour.metrics.formatter import PrometheusFormatter
from pykour.metrics.handler import MetricsHandler, setup_metrics
from pykour.metrics.middleware import MetricsMiddleware

__all__ = [
    "HistogramData",
    "MetricsCollector",
    "MetricsConfig",
    "MetricsHandler",
    "MetricsMiddleware",
    "PrometheusFormatter",
    "setup_metrics",
]
