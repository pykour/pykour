"""Tests for security headers middleware functionality."""

import pytest

from tests.helpers import create_noop_receive, create_noop_send
from pykour.middleware.security import (
    ContentSecurityPolicy,
    SecurityHeadersMiddleware,
)


class TestContentSecurityPolicy:
    """Tests for ContentSecurityPolicy configuration."""

    def test_default_csp(self) -> None:
        """Default CSP should have self as default-src."""
        csp = ContentSecurityPolicy()
        header = csp.to_header()
        assert header == "default-src 'self'"

    def test_multiple_directives(self) -> None:
        """Should combine multiple directives."""
        csp = ContentSecurityPolicy(
            default_src=["'self'"],
            script_src=["'self'", "https://cdn.example.com"],
            style_src=["'self'", "'unsafe-inline'"],
        )
        header = csp.to_header()

        assert "default-src 'self'" in header
        assert "script-src 'self' https://cdn.example.com" in header
        assert "style-src 'self' 'unsafe-inline'" in header

    def test_boolean_directives(self) -> None:
        """Should include boolean directives."""
        csp = ContentSecurityPolicy(
            upgrade_insecure_requests=True,
            block_all_mixed_content=True,
        )
        header = csp.to_header()

        assert "upgrade-insecure-requests" in header
        assert "block-all-mixed-content" in header

    def test_report_directives(self) -> None:
        """Should include reporting directives."""
        csp = ContentSecurityPolicy(
            report_uri="/csp-report",
            report_to="csp-endpoint",
        )
        header = csp.to_header()

        assert "report-uri /csp-report" in header
        assert "report-to csp-endpoint" in header

    def test_all_directives(self) -> None:
        """Should support all standard directives."""
        csp = ContentSecurityPolicy(
            default_src=["'self'"],
            script_src=["'self'"],
            style_src=["'self'"],
            img_src=["'self'", "data:"],
            font_src=["'self'"],
            connect_src=["'self'"],
            media_src=["'none'"],
            object_src=["'none'"],
            frame_src=["'none'"],
            frame_ancestors=["'none'"],
            form_action=["'self'"],
            base_uri=["'self'"],
        )
        header = csp.to_header()

        assert "img-src 'self' data:" in header
        assert "object-src 'none'" in header
        assert "frame-ancestors 'none'" in header


class TestSecurityHeadersMiddlewareConfig:
    """Tests for SecurityHeadersMiddleware configuration."""

    def test_default_headers(self) -> None:
        """Default configuration should set sensible headers."""
        middleware = SecurityHeadersMiddleware(None)

        # Check that headers are pre-computed
        header_names = [h[0] for h in middleware._headers]

        assert b"strict-transport-security" in header_names
        assert b"x-content-type-options" in header_names
        assert b"x-frame-options" in header_names
        assert b"x-xss-protection" in header_names
        assert b"referrer-policy" in header_names

    def test_custom_hsts(self) -> None:
        """Should support custom HSTS configuration."""
        middleware = SecurityHeadersMiddleware(
            None,
            hsts_max_age=63072000,  # 2 years
            hsts_include_subdomains=True,
            hsts_preload=True,
        )

        hsts_header = next(
            (h for h in middleware._headers if h[0] == b"strict-transport-security"),
            None,
        )
        assert hsts_header is not None

        value = hsts_header[1].decode()
        assert "max-age=63072000" in value
        assert "includeSubDomains" in value
        assert "preload" in value

    def test_disable_hsts(self) -> None:
        """Should allow disabling HSTS."""
        middleware = SecurityHeadersMiddleware(None, hsts_max_age=None)

        header_names = [h[0] for h in middleware._headers]
        assert b"strict-transport-security" not in header_names

    def test_custom_x_frame_options(self) -> None:
        """Should support custom X-Frame-Options."""
        middleware = SecurityHeadersMiddleware(None, x_frame_options="SAMEORIGIN")

        header = next(
            (h for h in middleware._headers if h[0] == b"x-frame-options"),
            None,
        )
        assert header is not None
        assert header[1] == b"SAMEORIGIN"

    def test_disable_x_frame_options(self) -> None:
        """Should allow disabling X-Frame-Options."""
        middleware = SecurityHeadersMiddleware(None, x_frame_options=None)

        header_names = [h[0] for h in middleware._headers]
        assert b"x-frame-options" not in header_names

    def test_csp_object(self) -> None:
        """Should support ContentSecurityPolicy object."""
        csp = ContentSecurityPolicy(
            default_src=["'self'"],
            script_src=["'self'", "https://cdn.example.com"],
        )
        middleware = SecurityHeadersMiddleware(None, content_security_policy=csp)

        header = next(
            (h for h in middleware._headers if h[0] == b"content-security-policy"),
            None,
        )
        assert header is not None
        assert b"script-src" in header[1]

    def test_csp_string(self) -> None:
        """Should support CSP as string."""
        middleware = SecurityHeadersMiddleware(
            None,
            content_security_policy="default-src 'self'; script-src 'unsafe-inline'",
        )

        header = next(
            (h for h in middleware._headers if h[0] == b"content-security-policy"),
            None,
        )
        assert header is not None
        assert b"unsafe-inline" in header[1]

    def test_csp_report_only(self) -> None:
        """Should support CSP report-only mode."""
        middleware = SecurityHeadersMiddleware(
            None,
            content_security_policy="default-src 'self'",
            csp_report_only=True,
        )

        header_names = [h[0] for h in middleware._headers]
        assert b"content-security-policy-report-only" in header_names
        assert b"content-security-policy" not in header_names

    def test_permissions_policy(self) -> None:
        """Should support Permissions-Policy."""
        middleware = SecurityHeadersMiddleware(
            None,
            permissions_policy={
                "geolocation": [],
                "camera": ["self"],
                "microphone": ["self", "https://example.com"],
            },
        )

        header = next(
            (h for h in middleware._headers if h[0] == b"permissions-policy"),
            None,
        )
        assert header is not None
        value = header[1].decode()
        assert "geolocation=()" in value
        assert "camera=" in value

    def test_cross_origin_policies(self) -> None:
        """Should support Cross-Origin policies."""
        middleware = SecurityHeadersMiddleware(
            None,
            cross_origin_embedder_policy="require-corp",
            cross_origin_opener_policy="same-origin",
            cross_origin_resource_policy="same-origin",
        )

        header_names = [h[0] for h in middleware._headers]
        assert b"cross-origin-embedder-policy" in header_names
        assert b"cross-origin-opener-policy" in header_names
        assert b"cross-origin-resource-policy" in header_names

    def test_cache_control(self) -> None:
        """Should support Cache-Control header."""
        middleware = SecurityHeadersMiddleware(
            None,
            cache_control="no-store, no-cache, must-revalidate",
        )

        header = next(
            (h for h in middleware._headers if h[0] == b"cache-control"),
            None,
        )
        assert header is not None
        assert b"no-store" in header[1]


class TestSecurityHeadersMiddlewareIntegration:
    """Integration tests for SecurityHeadersMiddleware."""

    @pytest.mark.asyncio
    async def test_adds_headers_to_response(self) -> None:
        """Should add security headers to response."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = SecurityHeadersMiddleware(mock_app)

        scope = {"type": "http", "path": "/test"}
        await middleware(scope, create_noop_receive(), mock_send)

        # Find response start message
        start_msg = next(
            m for m in messages_sent if m.get("type") == "http.response.start"
        )
        headers = dict(start_msg.get("headers", []))

        assert b"strict-transport-security" in headers
        assert b"x-content-type-options" in headers
        assert b"x-frame-options" in headers

    @pytest.mark.asyncio
    async def test_excludes_paths(self) -> None:
        """Should not add headers to excluded paths."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = SecurityHeadersMiddleware(
            mock_app,
            # Note: Use paths without trailing slash - match_prefix handles subpaths
            exclude_paths=["/health", "/static"],
        )

        # Test exact exclusion
        scope = {"type": "http", "path": "/health"}
        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(
            m for m in messages_sent if m.get("type") == "http.response.start"
        )
        headers = dict(start_msg.get("headers", []))
        assert b"strict-transport-security" not in headers

        # Test prefix exclusion
        messages_sent.clear()
        scope = {"type": "http", "path": "/static/js/app.js"}
        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(
            m for m in messages_sent if m.get("type") == "http.response.start"
        )
        headers = dict(start_msg.get("headers", []))
        assert b"strict-transport-security" not in headers

    @pytest.mark.asyncio
    async def test_non_http_passthrough(self) -> None:
        """Should pass through non-HTTP requests."""
        app_called = False

        async def mock_app(scope, receive, send):
            nonlocal app_called
            app_called = True

        middleware = SecurityHeadersMiddleware(mock_app)

        scope = {"type": "websocket", "path": "/ws"}
        await middleware(scope, create_noop_receive(), create_noop_send())

        assert app_called is True

    @pytest.mark.asyncio
    async def test_preserves_existing_headers(self) -> None:
        """Should preserve existing response headers."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"x-custom-header", b"custom-value"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": b"{}"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = SecurityHeadersMiddleware(mock_app)

        scope = {"type": "http", "path": "/api"}
        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(
            m for m in messages_sent if m.get("type") == "http.response.start"
        )
        headers = dict(start_msg.get("headers", []))

        # Original headers should be preserved
        assert headers.get(b"content-type") == b"application/json"
        assert headers.get(b"x-custom-header") == b"custom-value"

        # Security headers should be added
        assert b"strict-transport-security" in headers


class TestSecurityHeadersMiddlewareWithPykour:
    """Integration tests with Pykour application."""

    @pytest.mark.asyncio
    async def test_with_pykour_app(self, tmp_path) -> None:
        """Should work with actual Pykour application."""
        from pykour import Pykour
        from pykour.testing import TestClient

        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()

        (routes_dir / "route.py").write_text("""
from pykour import JSONResponse

async def get():
    return JSONResponse({"status": "ok"})
""")

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(SecurityHeadersMiddleware)

        client = TestClient(app)
        response = await client.get("/")

        assert response.status_code == 200
        assert "strict-transport-security" in response.headers
        assert "x-content-type-options" in response.headers
        assert "x-frame-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
