"""Tests for Prometheus metrics endpoint."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from pykour import Pykour

from tests.conftest import MockSend, create_receive, create_scope


ROUTES_DIR = Path(__file__).parent / "routes"


class TestMetricsConfig:
    """Test MetricsConfig dataclass."""

    def test_default_config(self) -> None:
        """Default metrics URL should be /metrics."""
        from pykour.metrics.config import MetricsConfig

        config = MetricsConfig()
        assert config.metrics_url == "/metrics"
        assert config.normalize_paths is True
        assert config.namespace == ""
        assert config.subsystem == "http"

    def test_custom_config(self) -> None:
        """Custom metrics configuration should be configurable."""
        from pykour.metrics.config import MetricsConfig

        config = MetricsConfig(
            metrics_url="/prometheus/metrics",
            namespace="myapp",
            subsystem="api",
            normalize_paths=False,
        )
        assert config.metrics_url == "/prometheus/metrics"
        assert config.namespace == "myapp"
        assert config.subsystem == "api"
        assert config.normalize_paths is False

    def test_disabled_config(self) -> None:
        """Metrics URL can be set to None to disable."""
        from pykour.metrics.config import MetricsConfig

        config = MetricsConfig(metrics_url=None)
        assert config.metrics_url is None

    def test_default_exclude_paths(self) -> None:
        """Default exclude paths should include /health and /metrics."""
        from pykour.metrics.config import MetricsConfig

        config = MetricsConfig()
        assert "/health" in config.exclude_paths
        assert "/metrics" in config.exclude_paths

    def test_latency_buckets(self) -> None:
        """Latency buckets should have sensible defaults."""
        from pykour.metrics.config import MetricsConfig

        config = MetricsConfig()
        assert len(config.latency_buckets) > 0
        assert config.latency_buckets[0] < config.latency_buckets[-1]


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_inc_requests_total(self) -> None:
        """Should increment total request count."""
        from pykour.metrics.collector import MetricsCollector

        collector = MetricsCollector(buckets=(0.1, 0.5, 1.0))

        collector.inc_requests_total("GET", "/api/users", "200")
        collector.inc_requests_total("GET", "/api/users", "200")
        collector.inc_requests_total("POST", "/api/users", "201")

        metrics = collector.collect()
        assert metrics["requests_total"][("GET", "/api/users", "200")] == 2
        assert metrics["requests_total"][("POST", "/api/users", "201")] == 1

    def test_observe_duration(self) -> None:
        """Should record request duration in histogram."""
        from pykour.metrics.collector import MetricsCollector

        collector = MetricsCollector(buckets=(0.1, 0.5, 1.0))

        collector.observe_duration("GET", "/api/users", 0.05)
        collector.observe_duration("GET", "/api/users", 0.3)

        metrics = collector.collect()
        data = metrics["request_duration"][("GET", "/api/users")]
        assert data.count == 2
        assert abs(data.sum - 0.35) < 0.001

    def test_in_progress_gauge(self) -> None:
        """Should track in-progress requests."""
        from pykour.metrics.collector import MetricsCollector

        collector = MetricsCollector(buckets=(0.1,))

        collector.inc_in_progress("GET", "/api")
        collector.inc_in_progress("GET", "/api")

        metrics = collector.collect()
        assert metrics["requests_in_progress"][("GET", "/api")] == 2

        collector.dec_in_progress("GET", "/api")
        metrics = collector.collect()
        assert metrics["requests_in_progress"][("GET", "/api")] == 1

    def test_dec_in_progress_not_negative(self) -> None:
        """In-progress count should not go negative."""
        from pykour.metrics.collector import MetricsCollector

        collector = MetricsCollector(buckets=(0.1,))

        collector.dec_in_progress("GET", "/api")
        collector.dec_in_progress("GET", "/api")

        metrics = collector.collect()
        assert metrics["requests_in_progress"][("GET", "/api")] == 0

    def test_add_response_size(self) -> None:
        """Should track total response size."""
        from pykour.metrics.collector import MetricsCollector

        collector = MetricsCollector(buckets=(0.1,))

        collector.add_response_size("GET", "/api", 100)
        collector.add_response_size("GET", "/api", 200)

        metrics = collector.collect()
        assert metrics["response_size_total"][("GET", "/api")] == 300

    def test_thread_safety(self) -> None:
        """Should be thread-safe for concurrent access."""
        from pykour.metrics.collector import MetricsCollector

        collector = MetricsCollector(buckets=(0.1,))

        def increment() -> None:
            for _ in range(1000):
                collector.inc_requests_total("GET", "/", "200")

        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        metrics = collector.collect()
        assert metrics["requests_total"][("GET", "/", "200")] == 10000

    def test_collect_returns_snapshot(self) -> None:
        """Collect should return a snapshot of metrics."""
        from pykour.metrics.collector import MetricsCollector

        collector = MetricsCollector(buckets=(0.1,))
        collector.inc_requests_total("GET", "/", "200")

        metrics1 = collector.collect()
        collector.inc_requests_total("GET", "/", "200")
        metrics2 = collector.collect()

        # First snapshot should not be affected by later changes
        assert metrics1["requests_total"][("GET", "/", "200")] == 1
        assert metrics2["requests_total"][("GET", "/", "200")] == 2


class TestPrometheusFormatter:
    """Test PrometheusFormatter class."""

    def test_format_counter(self) -> None:
        """Should format counter metric correctly."""
        from pykour.metrics.formatter import PrometheusFormatter

        formatter = PrometheusFormatter()
        metrics = {
            "requests_total": {("GET", "/api", "200"): 10},
            "request_duration": {},
            "requests_in_progress": {},
            "response_size_total": {},
        }

        output = formatter.format(metrics)
        assert 'http_requests_total{method="GET",path="/api",status="200"} 10' in output
        assert "# TYPE http_requests_total counter" in output
        assert "# HELP http_requests_total" in output

    def test_format_histogram(self) -> None:
        """Should format histogram metric correctly."""
        from pykour.metrics.collector import HistogramData
        from pykour.metrics.formatter import PrometheusFormatter

        formatter = PrometheusFormatter()
        metrics = {
            "requests_total": {},
            "request_duration": {
                ("GET", "/"): HistogramData(
                    buckets={0.1: 5, 0.5: 3, 1.0: 1},
                    sum=2.5,
                    count=9,
                )
            },
            "requests_in_progress": {},
            "response_size_total": {},
        }

        output = formatter.format(metrics)
        assert "http_request_duration_seconds_bucket" in output
        assert "http_request_duration_seconds_sum" in output
        assert "http_request_duration_seconds_count" in output
        assert 'le="+Inf"' in output

    def test_format_gauge(self) -> None:
        """Should format gauge metric correctly."""
        from pykour.metrics.formatter import PrometheusFormatter

        formatter = PrometheusFormatter()
        metrics = {
            "requests_total": {},
            "request_duration": {},
            "requests_in_progress": {("GET", "/api"): 5},
            "response_size_total": {},
        }

        output = formatter.format(metrics)
        assert 'http_requests_in_progress{method="GET",path="/api"} 5' in output
        assert "# TYPE http_requests_in_progress gauge" in output

    def test_format_with_namespace(self) -> None:
        """Should include namespace in metric names."""
        from pykour.metrics.formatter import PrometheusFormatter

        formatter = PrometheusFormatter(namespace="myapp", subsystem="http")
        metrics = {
            "requests_total": {("GET", "/", "200"): 1},
            "request_duration": {},
            "requests_in_progress": {},
            "response_size_total": {},
        }

        output = formatter.format(metrics)
        assert "myapp_http_requests_total" in output

    def test_escape_label_value(self) -> None:
        """Should escape special characters in label values."""
        from pykour.metrics.formatter import PrometheusFormatter

        formatter = PrometheusFormatter()
        # Backslash, double quote, and newline should be escaped
        assert (
            formatter._escape_label_value('test\\path"value\n')
            == 'test\\\\path\\"value\\n'
        )

    def test_empty_metrics(self) -> None:
        """Should return empty string for empty metrics."""
        from pykour.metrics.formatter import PrometheusFormatter

        formatter = PrometheusFormatter()
        metrics = {
            "requests_total": {},
            "request_duration": {},
            "requests_in_progress": {},
            "response_size_total": {},
        }

        output = formatter.format(metrics)
        assert output == ""


class TestMetricsHandler:
    """Test MetricsHandler class."""

    def test_handler_matches(self) -> None:
        """Handler should match the configured path."""
        from pykour.metrics.collector import MetricsCollector
        from pykour.metrics.config import MetricsConfig
        from pykour.metrics.handler import MetricsHandler

        config = MetricsConfig(metrics_url="/metrics")
        collector = MetricsCollector(buckets=(0.1,))
        handler = MetricsHandler(config, collector)

        assert handler.matches("/metrics") is True
        assert handler.matches("/prometheus") is False
        assert handler.matches("/") is False

    def test_handler_not_matches_when_disabled(self) -> None:
        """Handler should not match any path when URL is None."""
        from pykour.metrics.collector import MetricsCollector
        from pykour.metrics.config import MetricsConfig
        from pykour.metrics.handler import MetricsHandler

        config = MetricsConfig(metrics_url=None)
        collector = MetricsCollector(buckets=(0.1,))
        handler = MetricsHandler(config, collector)

        assert handler.matches("/metrics") is False

    async def test_handler_returns_prometheus_format(self) -> None:
        """Handler should return Prometheus formatted metrics."""
        from pykour.metrics.collector import MetricsCollector
        from pykour.metrics.config import MetricsConfig
        from pykour.metrics.handler import MetricsHandler

        config = MetricsConfig()
        collector = MetricsCollector(buckets=(0.1,))
        collector.inc_requests_total("GET", "/api", "200")

        handler = MetricsHandler(config, collector)

        scope = create_scope(method="GET", path="/metrics")
        receive = create_receive()
        send = MockSend()

        result = await handler.handle(scope, receive, send)

        assert result is True
        assert send.status == 200
        assert b"text/plain" in send.headers[b"content-type"]
        assert b"http_requests_total" in send.body

    async def test_handler_only_get_method(self) -> None:
        """Handler should only respond to GET requests."""
        from pykour.metrics.collector import MetricsCollector
        from pykour.metrics.config import MetricsConfig
        from pykour.metrics.handler import MetricsHandler

        config = MetricsConfig()
        collector = MetricsCollector(buckets=(0.1,))
        handler = MetricsHandler(config, collector)

        scope = create_scope(method="POST", path="/metrics")
        receive = create_receive()
        send = MockSend()

        result = await handler.handle(scope, receive, send)

        assert result is False


class TestMetricsMiddleware:
    """Test MetricsMiddleware class."""

    async def test_middleware_collects_metrics(self) -> None:
        """Middleware should collect request metrics."""
        from pykour.metrics.collector import MetricsCollector
        from pykour.metrics.config import MetricsConfig
        from pykour.metrics.middleware import MetricsMiddleware
        from pykour.response import JSONResponse

        async def app(scope, receive, send):
            response = JSONResponse({"status": "ok"})
            await response(scope, receive, send)

        config = MetricsConfig(exclude_paths=[])
        collector = MetricsCollector(buckets=(0.1, 0.5, 1.0))
        middleware = MetricsMiddleware(app, collector=collector, config=config)

        scope = create_scope(method="GET", path="/api/users")
        receive = create_receive()
        send = MockSend()

        await middleware(scope, receive, send)

        metrics = collector.collect()
        assert ("GET", "/api/users", "200") in metrics["requests_total"]
        assert ("GET", "/api/users") in metrics["request_duration"]

    async def test_middleware_excludes_paths(self) -> None:
        """Middleware should exclude configured paths from metrics."""
        from pykour.metrics.collector import MetricsCollector
        from pykour.metrics.config import MetricsConfig
        from pykour.metrics.middleware import MetricsMiddleware
        from pykour.response import JSONResponse

        async def app(scope, receive, send):
            response = JSONResponse({"status": "ok"})
            await response(scope, receive, send)

        config = MetricsConfig(exclude_paths=["/health", "/metrics"])
        collector = MetricsCollector(buckets=(0.1,))
        middleware = MetricsMiddleware(app, collector=collector, config=config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await middleware(scope, receive, send)

        metrics = collector.collect()
        assert len(metrics["requests_total"]) == 0

    async def test_middleware_normalizes_path(self) -> None:
        """Middleware should use path_pattern for normalization."""
        from pykour.metrics.collector import MetricsCollector
        from pykour.metrics.config import MetricsConfig
        from pykour.metrics.middleware import MetricsMiddleware
        from pykour.response import JSONResponse

        async def app(scope, receive, send):
            response = JSONResponse({"status": "ok"})
            await response(scope, receive, send)

        config = MetricsConfig(exclude_paths=[], normalize_paths=True)
        collector = MetricsCollector(buckets=(0.1,))
        middleware = MetricsMiddleware(app, collector=collector, config=config)

        # Scope with path_pattern set by router
        scope = create_scope(
            method="GET",
            path="/users/123",
            path_pattern="/users/{id}",
        )
        receive = create_receive()
        send = MockSend()

        await middleware(scope, receive, send)

        metrics = collector.collect()
        assert ("GET", "/users/{id}", "200") in metrics["requests_total"]

    async def test_middleware_passes_through_non_http(self) -> None:
        """Middleware should pass through non-HTTP requests."""
        from pykour.metrics.collector import MetricsCollector
        from pykour.metrics.config import MetricsConfig
        from pykour.metrics.middleware import MetricsMiddleware

        app_called = False

        async def app(scope, receive, send):
            nonlocal app_called
            app_called = True

        config = MetricsConfig()
        collector = MetricsCollector(buckets=(0.1,))
        middleware = MetricsMiddleware(app, collector=collector, config=config)

        scope = {"type": "websocket", "path": "/ws"}
        receive = create_receive()
        send = MockSend()

        await middleware(scope, receive, send)

        assert app_called is True
        metrics = collector.collect()
        assert len(metrics["requests_total"]) == 0


class TestMetricsEndpoint:
    """Integration tests for metrics endpoint."""

    async def test_metrics_endpoint_accessible(self) -> None:
        """Metrics endpoint should be accessible at /metrics."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/metrics")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        assert b"text/plain" in send.headers[b"content-type"]

    async def test_metrics_endpoint_custom_url(self) -> None:
        """Metrics endpoint should be accessible at custom URL."""
        app = Pykour(routes_dir=ROUTES_DIR, metrics_url="/prometheus/metrics")

        scope = create_scope(method="GET", path="/prometheus/metrics")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200

    async def test_metrics_endpoint_disabled(self) -> None:
        """Metrics endpoint should return 404 when disabled."""
        app = Pykour(routes_dir=ROUTES_DIR, metrics_url=None)

        scope = create_scope(method="GET", path="/metrics")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 404

    async def test_metrics_only_get_method(self) -> None:
        """Metrics endpoint should not respond to POST requests."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="POST", path="/metrics")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 404

    async def test_enable_metrics_collects_data(self) -> None:
        """enable_metrics should enable request metrics collection."""
        app = Pykour(routes_dir=ROUTES_DIR)
        app.enable_metrics()

        # Make a request to trigger metrics collection
        scope = create_scope(method="GET", path="/")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        # Check metrics endpoint has data
        scope = create_scope(method="GET", path="/metrics")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        body = send.body.decode("utf-8")
        assert "http_requests_total" in body

    async def test_enable_metrics_raises_when_disabled(self) -> None:
        """enable_metrics should raise when metrics_url is None."""
        app = Pykour(routes_dir=ROUTES_DIR, metrics_url=None)

        with pytest.raises(RuntimeError, match="Metrics endpoint is disabled"):
            app.enable_metrics()

    async def test_metrics_excludes_health_and_metrics(self) -> None:
        """Metrics collection should exclude /health and /metrics paths."""
        app = Pykour(routes_dir=ROUTES_DIR)
        app.enable_metrics()

        # Request health endpoint
        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()
        await app(scope, receive, send)

        # Request metrics endpoint
        scope = create_scope(method="GET", path="/metrics")
        receive = create_receive()
        send = MockSend()
        await app(scope, receive, send)

        # Check that /health and /metrics are not in metrics
        body = send.body.decode("utf-8")
        # These paths should not appear in the metrics output
        assert 'path="/health"' not in body
        assert 'path="/metrics"' not in body
