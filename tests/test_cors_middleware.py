"""Tests for CORS middleware functionality."""

import pytest

from tests.helpers import create_noop_receive, create_noop_send
from pykour import Pykour
from pykour.middleware.cors import CORSMiddleware


class TestCORSMiddlewareConfig:
    """Tests for CORS middleware configuration."""

    def test_default_config(self) -> None:
        """Default configuration should have sensible defaults."""
        middleware = CORSMiddleware(None)
        assert middleware.allow_origins == []
        assert middleware.allow_methods == ["GET"]
        assert middleware.allow_headers == []
        assert middleware.allow_credentials is False
        assert middleware.expose_headers == []
        assert middleware.max_age == 600

    def test_custom_config(self) -> None:
        """Custom configuration should be respected."""
        middleware = CORSMiddleware(
            None,
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization"],
            allow_credentials=True,
            expose_headers=["X-Custom"],
            max_age=3600,
        )
        assert middleware.allow_origins == ["https://example.com"]
        assert middleware.allow_methods == ["GET", "POST"]
        assert middleware.allow_headers == ["authorization"]  # lowercase
        assert middleware.allow_credentials is True
        assert middleware.expose_headers == ["X-Custom"]
        assert middleware.max_age == 3600

    def test_allow_all_origins(self) -> None:
        """Wildcard origin should be detected."""
        middleware = CORSMiddleware(None, allow_origins=["*"])
        assert middleware._allow_all_origins is True

    def test_wildcard_pattern_compilation(self) -> None:
        """Wildcard patterns should be compiled to regex."""
        middleware = CORSMiddleware(
            None,
            allow_origins=["https://*.example.com"],
        )
        assert len(middleware._origin_patterns) == 1
        assert middleware._origin_patterns[0].match("https://app.example.com")
        assert middleware._origin_patterns[0].match("https://api.example.com")
        assert not middleware._origin_patterns[0].match("https://example.com")


class TestCORSOriginValidation:
    """Tests for CORS origin validation."""

    def test_exact_origin_match(self) -> None:
        """Exact origin should be allowed."""
        middleware = CORSMiddleware(
            None,
            allow_origins=["https://example.com"],
        )
        assert middleware._is_origin_allowed("https://example.com") is True
        assert middleware._is_origin_allowed("https://other.com") is False

    def test_wildcard_all_origins(self) -> None:
        """Wildcard should allow all origins."""
        middleware = CORSMiddleware(None, allow_origins=["*"])
        assert middleware._is_origin_allowed("https://any.com") is True
        assert middleware._is_origin_allowed("http://localhost:3000") is True

    def test_pattern_origin_match(self) -> None:
        """Pattern origin should match subdomains."""
        middleware = CORSMiddleware(
            None,
            allow_origins=["https://*.example.com"],
        )
        assert middleware._is_origin_allowed("https://app.example.com") is True
        assert middleware._is_origin_allowed("https://api.example.com") is True
        assert middleware._is_origin_allowed("https://example.com") is False
        assert middleware._is_origin_allowed("https://other.com") is False


class TestCORSPreflightRequests:
    """Tests for CORS preflight request handling."""

    @pytest.mark.asyncio
    async def test_preflight_request_handling(self, tmp_path) -> None:
        """Preflight OPTIONS request should return CORS headers."""
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
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
            max_age=3600,
        )

        received_messages: list[dict] = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            received_messages.append(message)

        scope = {
            "type": "http",
            "method": "OPTIONS",
            "path": "/",
            "query_string": b"",
            "headers": [
                (b"origin", b"https://example.com"),
                (b"access-control-request-method", b"POST"),
                (b"access-control-request-headers", b"Authorization"),
            ],
        }

        await app(scope, receive, send)

        # Find the response.start message
        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        headers_dict = {
            k.decode().lower(): v.decode() for k, v in start_message["headers"]
        }

        assert "access-control-allow-origin" in headers_dict
        assert headers_dict["access-control-allow-origin"] == "https://example.com"
        assert "access-control-allow-methods" in headers_dict
        assert "GET" in headers_dict["access-control-allow-methods"]
        assert "POST" in headers_dict["access-control-allow-methods"]
        assert "access-control-max-age" in headers_dict
        assert headers_dict["access-control-max-age"] == "3600"

    @pytest.mark.asyncio
    async def test_preflight_with_credentials(self, tmp_path) -> None:
        """Preflight with credentials should include credentials header."""
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
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://example.com"],
            allow_credentials=True,
        )

        received_messages: list[dict] = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            received_messages.append(message)

        scope = {
            "type": "http",
            "method": "OPTIONS",
            "path": "/",
            "query_string": b"",
            "headers": [
                (b"origin", b"https://example.com"),
                (b"access-control-request-method", b"GET"),
            ],
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        headers_dict = {
            k.decode().lower(): v.decode() for k, v in start_message["headers"]
        }

        assert headers_dict.get("access-control-allow-credentials") == "true"


class TestCORSActualRequests:
    """Tests for CORS actual request handling."""

    @pytest.mark.asyncio
    async def test_cors_headers_on_actual_request(self, tmp_path) -> None:
        """Actual requests should have CORS headers added."""
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
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://example.com"],
        )

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
            "headers": [
                (b"origin", b"https://example.com"),
            ],
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        headers_dict = {
            k.decode().lower(): v.decode() for k, v in start_message["headers"]
        }

        assert headers_dict["access-control-allow-origin"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_cors_headers_with_expose_headers(self, tmp_path) -> None:
        """Expose headers should be included in response."""
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
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://example.com"],
            expose_headers=["X-Custom-Header", "X-Another-Header"],
        )

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
            "headers": [
                (b"origin", b"https://example.com"),
            ],
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        headers_dict = {
            k.decode().lower(): v.decode() for k, v in start_message["headers"]
        }

        assert "access-control-expose-headers" in headers_dict
        assert "X-Custom-Header" in headers_dict["access-control-expose-headers"]

    @pytest.mark.asyncio
    async def test_no_cors_headers_for_disallowed_origin(self, tmp_path) -> None:
        """Disallowed origins should not get CORS headers."""
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
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://example.com"],
        )

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
            "headers": [
                (b"origin", b"https://attacker.com"),
            ],
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        headers_dict = {
            k.decode().lower(): v.decode() for k, v in start_message["headers"]
        }

        assert "access-control-allow-origin" not in headers_dict

    @pytest.mark.asyncio
    async def test_wildcard_origin_response(self, tmp_path) -> None:
        """Wildcard origin should return '*' in response."""
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
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
        )

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
            "headers": [
                (b"origin", b"https://any-origin.com"),
            ],
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        headers_dict = {
            k.decode().lower(): v.decode() for k, v in start_message["headers"]
        }

        assert headers_dict["access-control-allow-origin"] == "*"


class TestCORSNonHttpRequests:
    """Tests for non-HTTP request handling."""

    @pytest.mark.asyncio
    async def test_non_http_requests_pass_through(self) -> None:
        """Non-HTTP requests should pass through without CORS processing."""
        called = False

        async def mock_app(scope, receive, send) -> None:
            nonlocal called
            called = True

        middleware = CORSMiddleware(
            mock_app,
            allow_origins=["*"],
        )

        await middleware(
            {"type": "websocket"}, create_noop_receive(), create_noop_send()
        )

        assert called is True


class TestCORSMiddlewareImport:
    """Tests for CORS middleware import."""

    def test_import_from_package(self) -> None:
        """CORSMiddleware can be imported from pykour.middleware."""
        from pykour.middleware import CORSMiddleware

        assert CORSMiddleware is not None

    def test_import_from_module(self) -> None:
        """CORSMiddleware can be imported from pykour.middleware.cors."""
        from pykour.middleware.cors import CORSMiddleware

        assert CORSMiddleware is not None
