"""Prometheus metrics endpoint handler."""

from pykour.metrics.collector import MetricsCollector
from pykour.metrics.config import MetricsConfig
from pykour.metrics.formatter import PrometheusFormatter
from pykour.response import Response
from pykour.types import Receive, Scope, Send


class MetricsHandler:
    """Handler for Prometheus metrics endpoint.

    This class handles requests to the metrics endpoint,
    returning collected metrics in Prometheus exposition format.

    Example:
        config = MetricsConfig(metrics_url="/metrics")
        collector = MetricsCollector(buckets=config.latency_buckets)
        handler = MetricsHandler(config, collector)

        # Check if path matches
        if handler.matches("/metrics"):
            await handler.handle(scope, receive, send)
    """

    def __init__(
        self,
        config: MetricsConfig,
        collector: MetricsCollector,
    ) -> None:
        """Initialize metrics handler.

        Args:
            config: Metrics configuration.
            collector: Metrics collector instance.
        """
        self._config = config
        self._collector = collector
        self._formatter = PrometheusFormatter(
            namespace=config.namespace,
            subsystem=config.subsystem,
        )

    def matches(self, path: str) -> bool:
        """Check if the path matches the metrics endpoint.

        Args:
            path: Request path.

        Returns:
            True if path matches the metrics endpoint.
        """
        return path == self._config.metrics_url

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> bool:
        """Handle metrics request.

        Args:
            scope: ASGI scope.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            True if the request was handled, False otherwise.
        """
        path = scope.get("path", "/")
        method = scope.get("method", "GET")

        # Only handle GET requests for metrics
        if method != "GET":
            return False

        if path == self._config.metrics_url:
            metrics = self._collector.collect()
            content = self._formatter.format(metrics)

            response = Response(
                content=content,
                status_code=200,
                media_type=PrometheusFormatter.CONTENT_TYPE,
            )
            await response(scope, receive, send)
            return True

        return False


def setup_metrics(
    config: MetricsConfig,
    collector: MetricsCollector,
) -> MetricsHandler:
    """Set up metrics endpoint for a Pykour application.

    Args:
        config: Metrics configuration.
        collector: Metrics collector instance.

    Returns:
        Metrics handler instance.
    """
    return MetricsHandler(config, collector)
