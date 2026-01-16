"""Tests for logging middleware."""

import logging

import pytest

from tests.helpers import create_noop_receive, create_noop_send
from pykour import Pykour
from pykour.middleware.logging import LoggingMiddleware


class TestLoggingMiddlewareConfig:
    """Tests for logging middleware configuration."""

    def test_default_config(self) -> None:
        """Default configuration should have sensible defaults."""
        middleware = LoggingMiddleware(None)
        assert middleware.logger.name == "pykour.access"
        assert middleware.level == logging.INFO
        assert middleware.exclude_paths == []
        assert middleware.log_request_headers is False
        assert middleware.log_response_headers is False

    def test_custom_config(self) -> None:
        """Custom configuration should be respected."""
        middleware = LoggingMiddleware(
            None,
            logger_name="custom.logger",
            level="DEBUG",
            exclude_paths=["/health", "/metrics"],
            log_request_headers=True,
            log_response_headers=True,
        )
        assert middleware.logger.name == "custom.logger"
        assert middleware.level == logging.DEBUG
        assert middleware.exclude_paths == ["/health", "/metrics"]
        assert middleware.log_request_headers is True
        assert middleware.log_response_headers is True

    def test_level_as_int(self) -> None:
        """Log level can be provided as int."""
        middleware = LoggingMiddleware(None, level=logging.WARNING)
        assert middleware.level == logging.WARNING

    def test_level_case_insensitive(self) -> None:
        """Log level string is case insensitive."""
        middleware = LoggingMiddleware(None, level="warning")
        assert middleware.level == logging.WARNING


class TestLoggingPathExclusion:
    """Tests for path exclusion."""

    def test_exact_path_excluded(self) -> None:
        """Exact path match should be excluded."""
        middleware = LoggingMiddleware(
            None,
            exclude_paths=["/health", "/metrics"],
        )
        assert middleware._is_excluded("/health") is True
        assert middleware._is_excluded("/metrics") is True
        assert middleware._is_excluded("/api") is False

    def test_path_prefix_excluded(self) -> None:
        """Paths with excluded prefix should be excluded."""
        middleware = LoggingMiddleware(
            None,
            exclude_paths=["/internal"],
        )
        assert middleware._is_excluded("/internal") is True
        assert middleware._is_excluded("/internal/status") is True
        assert middleware._is_excluded("/internaldata") is False


class TestLoggingClientIP:
    """Tests for client IP extraction."""

    def test_client_ip_from_client_tuple(self) -> None:
        """Client IP should be extracted from client tuple."""
        middleware = LoggingMiddleware(None)
        scope = {"client": ("192.168.1.100", 12345)}
        assert middleware._get_client_ip(scope) == "192.168.1.100"

    def test_client_ip_from_x_forwarded_for(self) -> None:
        """Client IP should be extracted from X-Forwarded-For header."""
        middleware = LoggingMiddleware(None)
        scope = {
            "client": ("127.0.0.1", 8080),
            "headers": [
                (b"x-forwarded-for", b"203.0.113.50, 70.41.3.18, 150.172.238.178")
            ],
        }
        assert middleware._get_client_ip(scope) == "203.0.113.50"

    def test_client_ip_missing(self) -> None:
        """Missing client info should return '-'."""
        middleware = LoggingMiddleware(None)
        scope = {}
        assert middleware._get_client_ip(scope) == "-"


class TestLoggingStatusLevel:
    """Tests for status code to log level mapping."""

    def test_success_status_is_info(self) -> None:
        """2xx status codes should use INFO level."""
        middleware = LoggingMiddleware(None)
        assert middleware._get_status_level(200) == logging.INFO
        assert middleware._get_status_level(201) == logging.INFO
        assert middleware._get_status_level(204) == logging.INFO

    def test_redirect_status_is_info(self) -> None:
        """3xx status codes should use INFO level."""
        middleware = LoggingMiddleware(None)
        assert middleware._get_status_level(301) == logging.INFO
        assert middleware._get_status_level(302) == logging.INFO
        assert middleware._get_status_level(304) == logging.INFO

    def test_client_error_is_warning(self) -> None:
        """4xx status codes should use WARNING level."""
        middleware = LoggingMiddleware(None)
        assert middleware._get_status_level(400) == logging.WARNING
        assert middleware._get_status_level(401) == logging.WARNING
        assert middleware._get_status_level(404) == logging.WARNING
        assert middleware._get_status_level(422) == logging.WARNING

    def test_server_error_is_error(self) -> None:
        """5xx status codes should use ERROR level."""
        middleware = LoggingMiddleware(None)
        assert middleware._get_status_level(500) == logging.ERROR
        assert middleware._get_status_level(502) == logging.ERROR
        assert middleware._get_status_level(503) == logging.ERROR


class TestLoggingHeaderFormat:
    """Tests for header formatting."""

    def test_format_headers(self) -> None:
        """Headers should be formatted correctly."""
        middleware = LoggingMiddleware(None)
        headers = [
            (b"content-type", b"application/json"),
            (b"x-custom", b"value"),
        ]
        result = middleware._format_headers(headers)
        assert "content-type: application/json" in result
        assert "x-custom: value" in result

    def test_sensitive_headers_redacted(self) -> None:
        """Sensitive headers should be redacted."""
        middleware = LoggingMiddleware(None)
        headers = [
            (b"authorization", b"Bearer secret-token"),
            (b"cookie", b"session=abc123"),
            (b"set-cookie", b"session=xyz789"),
        ]
        result = middleware._format_headers(headers)
        assert "authorization: [REDACTED]" in result
        assert "cookie: [REDACTED]" in result
        assert "set-cookie: [REDACTED]" in result
        assert "secret-token" not in result
        assert "abc123" not in result


class TestLoggingMiddlewareIntegration:
    """Integration tests for logging middleware."""

    @pytest.mark.asyncio
    async def test_logging_on_successful_request(self, tmp_path, caplog) -> None:
        """Successful request should be logged at INFO level."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(LoggingMiddleware)

        received_messages: list[dict] = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            received_messages.append(message)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }

        with caplog.at_level(logging.INFO, logger="pykour.access"):
            await app(scope, receive, send)

        # Verify request completed successfully
        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        assert start_message["status"] == 200

        # Verify log was recorded
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelno == logging.INFO
        assert "GET /" in record.message
        assert "200" in record.message
        assert "127.0.0.1" in record.message
        assert "ms" in record.message

    @pytest.mark.asyncio
    async def test_logging_on_404_request(self, tmp_path, caplog) -> None:
        """404 request should be logged at WARNING level."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(LoggingMiddleware)

        received_messages: list[dict] = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            received_messages.append(message)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/nonexistent",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }

        with caplog.at_level(logging.WARNING, logger="pykour.access"):
            await app(scope, receive, send)

        # Verify 404 response
        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        assert start_message["status"] == 404

        # Verify log was recorded at WARNING level
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelno == logging.WARNING
        assert "404" in record.message

    @pytest.mark.asyncio
    async def test_excluded_path_not_logged(self, tmp_path, caplog) -> None:
        """Excluded paths should not be logged."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        health_dir = routes_dir / "health"
        health_dir.mkdir()
        (health_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"status": "healthy"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(
            LoggingMiddleware,
            exclude_paths=["/health"],
        )

        received_messages: list[dict] = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            received_messages.append(message)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }

        with caplog.at_level(logging.DEBUG, logger="pykour.access"):
            await app(scope, receive, send)

        # Verify request completed successfully
        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        assert start_message["status"] == 200

        # Verify no log was recorded
        assert len(caplog.records) == 0

    @pytest.mark.asyncio
    async def test_query_string_in_log(self, tmp_path, caplog) -> None:
        """Query string should be included in log."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(LoggingMiddleware)

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"page=1&limit=10",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }

        with caplog.at_level(logging.INFO, logger="pykour.access"):
            await app(scope, receive, send)

        assert len(caplog.records) == 1
        assert "/?page=1&limit=10" in caplog.records[0].message

    @pytest.mark.asyncio
    async def test_non_http_requests_pass_through(self) -> None:
        """Non-HTTP requests should pass through without logging."""
        called = False

        async def mock_app(scope, receive, send) -> None:
            nonlocal called
            called = True

        middleware = LoggingMiddleware(mock_app)
        await middleware(
            {"type": "websocket"}, create_noop_receive(), create_noop_send()
        )

        assert called is True


class TestLoggingMiddlewareImport:
    """Tests for logging middleware import."""

    def test_import_from_package(self) -> None:
        """LoggingMiddleware can be imported from pykour.middleware."""
        from pykour.middleware import LoggingMiddleware

        assert LoggingMiddleware is not None

    def test_import_from_module(self) -> None:
        """LoggingMiddleware can be imported from pykour.middleware.logging."""
        from pykour.middleware.logging import LoggingMiddleware

        assert LoggingMiddleware is not None


class TestLoggingMiddlewareJsonFormat:
    """Tests for JSON format output."""

    def test_json_format_config(self) -> None:
        """JSON format configuration should be accepted."""
        middleware = LoggingMiddleware(None, format="json")
        assert middleware.format == "json"

    def test_text_format_default(self) -> None:
        """Text format should be the default."""
        middleware = LoggingMiddleware(None)
        assert middleware.format == "text"

    def test_get_user_agent(self) -> None:
        """User-Agent header should be extracted correctly."""
        middleware = LoggingMiddleware(None)
        scope = {
            "headers": [
                (b"user-agent", b"Mozilla/5.0 (Test)"),
            ]
        }
        assert middleware._get_user_agent(scope) == "Mozilla/5.0 (Test)"

    def test_get_user_agent_missing(self) -> None:
        """Missing User-Agent should return '-'."""
        middleware = LoggingMiddleware(None)
        scope = {"headers": []}
        assert middleware._get_user_agent(scope) == "-"

    def test_get_content_length(self) -> None:
        """Content-Length header should be extracted correctly."""
        middleware = LoggingMiddleware(None)
        scope = {
            "headers": [
                (b"content-length", b"1024"),
            ]
        }
        assert middleware._get_content_length(scope) == 1024

    def test_get_content_length_missing(self) -> None:
        """Missing Content-Length should return 0."""
        middleware = LoggingMiddleware(None)
        scope = {"headers": []}
        assert middleware._get_content_length(scope) == 0

    def test_get_content_length_invalid(self) -> None:
        """Invalid Content-Length should return 0."""
        middleware = LoggingMiddleware(None)
        scope = {
            "headers": [
                (b"content-length", b"not-a-number"),
            ]
        }
        assert middleware._get_content_length(scope) == 0

    @pytest.mark.asyncio
    async def test_json_format_output(self, tmp_path, caplog) -> None:
        """JSON format should produce valid JSON log output."""
        import json

        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(LoggingMiddleware, format="json")

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"page=1",
            "headers": [
                (b"user-agent", b"TestClient/1.0"),
                (b"content-length", b"0"),
            ],
            "client": ("192.168.1.100", 12345),
        }

        with caplog.at_level(logging.INFO, logger="pykour.access"):
            await app(scope, receive, send)

        assert len(caplog.records) == 1
        record = caplog.records[0]

        # Parse the JSON output
        log_data = json.loads(record.message)

        assert log_data["type"] == "access"
        assert log_data["method"] == "GET"
        assert log_data["path"] == "/"
        assert log_data["query_string"] == "page=1"
        assert log_data["status_code"] == 200
        assert log_data["client_ip"] == "192.168.1.100"
        assert log_data["user_agent"] == "TestClient/1.0"
        assert "duration_ms" in log_data
        assert "timestamp" in log_data
        assert "trace_id" in log_data
