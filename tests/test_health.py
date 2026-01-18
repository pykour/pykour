"""Tests for health check endpoint."""

import json
from pathlib import Path

from pykour import Pykour
from pykour.health import HealthCheckConfig, HealthCheckHandler, HealthStatus

from tests.conftest import MockSend, create_receive, create_scope


ROUTES_DIR = Path(__file__).parent / "routes"


class TestHealthCheckEndpoint:
    """Test health check endpoint functionality."""

    async def test_health_check_default_url(self) -> None:
        """Health check should be accessible at /health by default."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        assert json.loads(send.body) == {"status": "ok"}

    async def test_health_check_custom_url(self) -> None:
        """Health check should be accessible at custom URL."""
        app = Pykour(routes_dir=ROUTES_DIR, health_url="/healthz")

        scope = create_scope(method="GET", path="/healthz")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        assert json.loads(send.body) == {"status": "ok"}

    async def test_health_check_disabled(self) -> None:
        """Health check should return 404 when disabled."""
        app = Pykour(routes_dir=ROUTES_DIR, health_url=None)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 404

    async def test_health_check_only_get_method(self) -> None:
        """Health check should not respond to POST requests."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="POST", path="/health")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        # Should not be handled by health check handler
        assert send.status == 404

    async def test_health_check_does_not_conflict_with_routes(self) -> None:
        """Health check should not conflict with custom routes."""
        app = Pykour(routes_dir=ROUTES_DIR, health_url="/api/health")

        # Custom health endpoint
        scope = create_scope(method="GET", path="/api/health")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        assert json.loads(send.body) == {"status": "ok"}

        # Root route should still work
        scope = create_scope(method="GET", path="/")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200


class TestHealthCheckConfig:
    """Test health check configuration."""

    async def test_default_config(self) -> None:
        """Default health URL should be /health."""
        from pykour.health.config import HealthCheckConfig

        config = HealthCheckConfig()
        assert config.health_url == "/health"

    async def test_custom_config(self) -> None:
        """Custom health URL should be configurable."""
        from pykour.health.config import HealthCheckConfig

        config = HealthCheckConfig(health_url="/status")
        assert config.health_url == "/status"

    async def test_disabled_config(self) -> None:
        """Health URL can be set to None to disable."""
        from pykour.health.config import HealthCheckConfig

        config = HealthCheckConfig(health_url=None)
        assert config.health_url is None


class TestHealthCheckHandler:
    """Test health check handler."""

    async def test_handler_matches(self) -> None:
        """Handler should match the configured path."""
        from pykour.health.config import HealthCheckConfig
        from pykour.health.handler import HealthCheckHandler

        config = HealthCheckConfig(health_url="/health")
        handler = HealthCheckHandler(config)

        assert handler.matches("/health") is True
        assert handler.matches("/healthz") is False
        assert handler.matches("/") is False

    async def test_handler_not_matches_when_disabled(self) -> None:
        """Handler should not match any path when URL is None."""
        from pykour.health.config import HealthCheckConfig
        from pykour.health.handler import HealthCheckHandler

        config = HealthCheckConfig(health_url=None)
        handler = HealthCheckHandler(config)

        assert handler.matches("/health") is False
        assert handler.matches("/healthz") is False
        assert handler.matches("/") is False


class TestHealthStatus:
    """Test HealthStatus class."""

    def test_health_status_basic(self) -> None:
        """HealthStatus should store basic fields."""
        status = HealthStatus(name="database", status="healthy")
        assert status.name == "database"
        assert status.status == "healthy"
        assert status.latency_ms is None
        assert status.error is None

    def test_health_status_with_latency(self) -> None:
        """HealthStatus should store latency."""
        status = HealthStatus(name="cache", status="healthy", latency_ms=5.5)
        assert status.latency_ms == 5.5

    def test_health_status_with_error(self) -> None:
        """HealthStatus should store error message."""
        status = HealthStatus(
            name="database", status="unhealthy", error="Connection timeout"
        )
        assert status.error == "Connection timeout"

    def test_health_status_to_dict(self) -> None:
        """HealthStatus should convert to dict correctly."""
        status = HealthStatus(
            name="database",
            status="healthy",
            latency_ms=10.5,
        )
        result = status.to_dict()
        assert result == {
            "name": "database",
            "status": "healthy",
            "latency_ms": 10.5,
        }

    def test_health_status_to_dict_with_error(self) -> None:
        """HealthStatus should include error in dict when present."""
        status = HealthStatus(
            name="cache",
            status="unhealthy",
            error="Timeout",
        )
        result = status.to_dict()
        assert result == {
            "name": "cache",
            "status": "unhealthy",
            "error": "Timeout",
        }

    def test_health_status_to_dict_with_details(self) -> None:
        """HealthStatus should include details in dict when present."""
        status = HealthStatus(
            name="database",
            status="healthy",
            details={"connections": 5, "pool_size": 10},
        )
        result = status.to_dict()
        assert result == {
            "name": "database",
            "status": "healthy",
            "details": {"connections": 5, "pool_size": 10},
        }


class TestHealthCheckConfigExtended:
    """Test extended HealthCheckConfig."""

    def test_include_details_default_false(self) -> None:
        """include_details should default to False."""
        config = HealthCheckConfig()
        assert config.include_details is False

    def test_include_details_configurable(self) -> None:
        """include_details should be configurable."""
        config = HealthCheckConfig(include_details=True)
        assert config.include_details is True

    def test_checks_default_empty(self) -> None:
        """checks should default to empty list."""
        config = HealthCheckConfig()
        assert config.checks == []

    def test_version_default_none(self) -> None:
        """version should default to None."""
        config = HealthCheckConfig()
        assert config.version is None

    def test_version_configurable(self) -> None:
        """version should be configurable."""
        config = HealthCheckConfig(version="1.0.0")
        assert config.version == "1.0.0"


class TestHealthCheckHandlerExtended:
    """Test extended HealthCheckHandler functionality."""

    async def test_detailed_response(self) -> None:
        """Handler should include details when configured."""
        config = HealthCheckConfig(
            health_url="/health",
            include_details=True,
        )
        handler = HealthCheckHandler(config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        assert send.status == 200
        body = json.loads(send.body)
        assert body["status"] == "healthy"
        assert "uptime_seconds" in body
        assert body["uptime_seconds"] >= 0

    async def test_detailed_response_with_version(self) -> None:
        """Handler should include version when configured."""
        config = HealthCheckConfig(
            health_url="/health",
            include_details=True,
            version="1.2.3",
        )
        handler = HealthCheckHandler(config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        body = json.loads(send.body)
        assert body["version"] == "1.2.3"

    async def test_custom_health_check(self) -> None:
        """Handler should run custom health checks."""

        async def check_database() -> HealthStatus:
            return HealthStatus(name="database", status="healthy")

        config = HealthCheckConfig(
            health_url="/health",
            include_details=True,
            checks=[check_database],
        )
        handler = HealthCheckHandler(config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        assert send.status == 200
        body = json.loads(send.body)
        assert body["status"] == "healthy"
        assert len(body["checks"]) == 1
        assert body["checks"][0]["name"] == "database"
        assert body["checks"][0]["status"] == "healthy"
        assert "latency_ms" in body["checks"][0]

    async def test_multiple_health_checks(self) -> None:
        """Handler should run multiple health checks."""

        async def check_database() -> HealthStatus:
            return HealthStatus(name="database", status="healthy")

        async def check_cache() -> HealthStatus:
            return HealthStatus(name="cache", status="healthy")

        config = HealthCheckConfig(
            health_url="/health",
            include_details=True,
            checks=[check_database, check_cache],
        )
        handler = HealthCheckHandler(config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        body = json.loads(send.body)
        assert len(body["checks"]) == 2
        assert body["checks"][0]["name"] == "database"
        assert body["checks"][1]["name"] == "cache"

    async def test_unhealthy_check_returns_503(self) -> None:
        """Handler should return 503 when a check is unhealthy."""

        async def check_database() -> HealthStatus:
            return HealthStatus(name="database", status="unhealthy", error="Down")

        config = HealthCheckConfig(
            health_url="/health",
            include_details=True,
            checks=[check_database],
        )
        handler = HealthCheckHandler(config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        assert send.status == 503
        body = json.loads(send.body)
        assert body["status"] == "unhealthy"

    async def test_degraded_check(self) -> None:
        """Handler should report degraded status."""

        async def check_cache() -> HealthStatus:
            return HealthStatus(name="cache", status="degraded")

        config = HealthCheckConfig(
            health_url="/health",
            include_details=True,
            checks=[check_cache],
        )
        handler = HealthCheckHandler(config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        assert send.status == 503
        body = json.loads(send.body)
        assert body["status"] == "degraded"

    async def test_check_exception_marks_unhealthy(self) -> None:
        """Handler should mark check as unhealthy on exception."""

        async def failing_check() -> HealthStatus:
            raise RuntimeError("Database connection failed")

        config = HealthCheckConfig(
            health_url="/health",
            include_details=True,
            checks=[failing_check],
        )
        handler = HealthCheckHandler(config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        assert send.status == 503
        body = json.loads(send.body)
        assert body["status"] == "unhealthy"
        assert body["checks"][0]["status"] == "unhealthy"
        assert "Database connection failed" in body["checks"][0]["error"]

    async def test_add_check_method(self) -> None:
        """Handler should support adding checks via method."""
        config = HealthCheckConfig(
            health_url="/health",
            include_details=True,
        )
        handler = HealthCheckHandler(config)

        async def check_cache() -> HealthStatus:
            return HealthStatus(name="cache", status="healthy")

        handler.add_check(check_cache)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        body = json.loads(send.body)
        assert len(body["checks"]) == 1
        assert body["checks"][0]["name"] == "cache"

    async def test_simple_response_without_details(self) -> None:
        """Handler should return simple response when include_details is False."""

        async def check_database() -> HealthStatus:
            return HealthStatus(name="database", status="healthy")

        config = HealthCheckConfig(
            health_url="/health",
            include_details=False,
            checks=[check_database],
        )
        handler = HealthCheckHandler(config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        assert send.status == 200
        body = json.loads(send.body)
        assert body == {"status": "ok"}
        assert "checks" not in body
        assert "uptime_seconds" not in body

    async def test_simple_response_unhealthy_without_details(self) -> None:
        """Handler should return unhealthy status in simple mode."""

        async def check_database() -> HealthStatus:
            return HealthStatus(name="database", status="unhealthy")

        config = HealthCheckConfig(
            health_url="/health",
            include_details=False,
            checks=[check_database],
        )
        handler = HealthCheckHandler(config)

        scope = create_scope(method="GET", path="/health")
        receive = create_receive()
        send = MockSend()

        await handler.handle(scope, receive, send)

        assert send.status == 503
        body = json.loads(send.body)
        assert body == {"status": "unhealthy"}
