"""Tests for CSRF middleware functionality."""

from __future__ import annotations

import pytest

from pykour.middleware.csrf import CSRFMiddleware, SAFE_METHODS
from tests.helpers import create_noop_receive, create_noop_send, create_scope, MockSend


class TestCSRFMiddlewareConfig:
    """Tests for CSRFMiddleware configuration."""

    def test_default_config(self) -> None:
        """Default configuration should have sensible defaults."""
        middleware = CSRFMiddleware(None)

        assert middleware.cookie_name == "csrf_token"
        assert middleware.header_name == "X-CSRF-Token"
        assert middleware.cookie_path == "/"
        assert middleware.cookie_domain is None
        assert middleware.cookie_secure is False
        assert middleware.cookie_httponly is False
        assert middleware.cookie_samesite == "Lax"
        assert middleware.cookie_max_age == 86400
        assert middleware.token_bytes == 32
        assert middleware.exclude_paths == []
        assert middleware.safe_methods == SAFE_METHODS

    def test_custom_config(self) -> None:
        """Custom configuration should be respected."""
        middleware = CSRFMiddleware(
            None,
            cookie_name="my_csrf",
            header_name="X-My-CSRF",
            cookie_path="/api",
            cookie_domain="example.com",
            cookie_secure=True,
            cookie_httponly=True,
            cookie_samesite="Strict",
            cookie_max_age=7200,
            token_bytes=64,
            exclude_paths=["/webhook", "/health"],
            exclude_methods=["PATCH"],
        )

        assert middleware.cookie_name == "my_csrf"
        assert middleware.header_name == "X-My-CSRF"
        assert middleware.cookie_path == "/api"
        assert middleware.cookie_domain == "example.com"
        assert middleware.cookie_secure is True
        assert middleware.cookie_httponly is True
        assert middleware.cookie_samesite == "Strict"
        assert middleware.cookie_max_age == 7200
        assert middleware.token_bytes == 64
        assert middleware.exclude_paths == ["/webhook", "/health"]
        assert "PATCH" in middleware.safe_methods


class TestCSRFTokenGeneration:
    """Tests for CSRF token generation."""

    def test_token_generation_returns_hex_string(self) -> None:
        """Generated tokens should be hex strings."""
        middleware = CSRFMiddleware(None)
        token = middleware._generate_token()

        # Should be a valid hex string
        assert all(c in "0123456789abcdef" for c in token)

    def test_token_generation_default_length(self) -> None:
        """Generated tokens should have correct default length."""
        middleware = CSRFMiddleware(None)
        token = middleware._generate_token()

        # Default 32 bytes = 64 hex chars
        assert len(token) == 64

    def test_token_generation_custom_length(self) -> None:
        """Generated tokens should respect custom token_bytes."""
        middleware = CSRFMiddleware(None, token_bytes=16)
        token = middleware._generate_token()

        # 16 bytes = 32 hex chars
        assert len(token) == 32

    def test_token_generation_unique(self) -> None:
        """Generated tokens should be unique."""
        middleware = CSRFMiddleware(None)

        tokens = {middleware._generate_token() for _ in range(100)}

        # All tokens should be unique
        assert len(tokens) == 100


class TestCSRFTokenVerification:
    """Tests for CSRF token verification."""

    def test_verify_matching_tokens(self) -> None:
        """Matching tokens should verify successfully."""
        middleware = CSRFMiddleware(None)
        token = "abc123xyz789"

        assert middleware._verify_tokens(token, token) is True

    def test_verify_mismatching_tokens(self) -> None:
        """Mismatching tokens should fail verification."""
        middleware = CSRFMiddleware(None)

        assert middleware._verify_tokens("abc123", "xyz789") is False

    def test_verify_empty_cookie_token(self) -> None:
        """Empty cookie token should fail verification."""
        middleware = CSRFMiddleware(None)

        assert middleware._verify_tokens("", "abc123") is False

    def test_verify_empty_header_token(self) -> None:
        """Empty header token should fail verification."""
        middleware = CSRFMiddleware(None)

        assert middleware._verify_tokens("abc123", "") is False

    def test_verify_both_empty_tokens(self) -> None:
        """Both empty tokens should fail verification."""
        middleware = CSRFMiddleware(None)

        assert middleware._verify_tokens("", "") is False


class TestCSRFCookieParsing:
    """Tests for CSRF cookie parsing."""

    def test_get_cookie_token_exists(self) -> None:
        """Should extract token from cookie header."""
        middleware = CSRFMiddleware(None)
        scope = create_scope(headers=[(b"cookie", b"csrf_token=abc123")])

        token = middleware._get_cookie_token(scope)

        assert token == "abc123"

    def test_get_cookie_token_missing(self) -> None:
        """Should return None when cookie not present."""
        middleware = CSRFMiddleware(None)
        scope = create_scope()

        token = middleware._get_cookie_token(scope)

        assert token is None

    def test_get_cookie_token_custom_name(self) -> None:
        """Should extract token with custom cookie name."""
        middleware = CSRFMiddleware(None, cookie_name="my_csrf")
        scope = create_scope(headers=[(b"cookie", b"my_csrf=xyz789")])

        token = middleware._get_cookie_token(scope)

        assert token == "xyz789"

    def test_get_cookie_token_among_multiple(self) -> None:
        """Should extract correct token among multiple cookies."""
        middleware = CSRFMiddleware(None)
        scope = create_scope(
            headers=[(b"cookie", b"session=abc; csrf_token=xyz123; user=john")]
        )

        token = middleware._get_cookie_token(scope)

        assert token == "xyz123"


class TestCSRFHeaderExtraction:
    """Tests for CSRF header extraction."""

    def test_get_header_token_exists(self) -> None:
        """Should extract token from header."""
        middleware = CSRFMiddleware(None)
        scope = create_scope(headers=[(b"x-csrf-token", b"abc123")])

        token = middleware._get_header_token(scope)

        assert token == "abc123"

    def test_get_header_token_missing(self) -> None:
        """Should return None when header not present."""
        middleware = CSRFMiddleware(None)
        scope = create_scope()

        token = middleware._get_header_token(scope)

        assert token is None

    def test_get_header_token_custom_name(self) -> None:
        """Should extract token with custom header name."""
        middleware = CSRFMiddleware(None, header_name="X-My-Token")
        scope = create_scope(headers=[(b"x-my-token", b"xyz789")])

        token = middleware._get_header_token(scope)

        assert token == "xyz789"


class TestCSRFMiddlewareIntegration:
    """Integration tests for CSRFMiddleware."""

    @pytest.mark.asyncio
    async def test_non_http_passthrough(self) -> None:
        """Non-HTTP requests should pass through."""
        called = False

        async def mock_app(scope, receive, send) -> None:
            nonlocal called
            called = True

        middleware = CSRFMiddleware(mock_app)
        scope = {"type": "websocket"}

        await middleware(scope, create_noop_receive(), create_noop_send())

        assert called is True

    @pytest.mark.asyncio
    async def test_get_request_without_cookie_sets_cookie(self) -> None:
        """GET request without cookie should set CSRF cookie."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = CSRFMiddleware(mock_app)
        scope = create_scope(method="GET", path="/")

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        headers = dict(start_msg["headers"])

        assert b"set-cookie" in headers
        cookie_value = headers[b"set-cookie"].decode()
        assert "csrf_token=" in cookie_value

    @pytest.mark.asyncio
    async def test_get_request_with_cookie_passthrough(self) -> None:
        """GET request with cookie should pass through without new cookie."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = CSRFMiddleware(mock_app)
        scope = create_scope(
            method="GET",
            path="/",
            headers=[(b"cookie", b"csrf_token=existing_token")],
        )

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        headers = dict(start_msg["headers"])

        # Should not have Set-Cookie header
        assert b"set-cookie" not in headers

    @pytest.mark.asyncio
    async def test_post_without_cookie_rejected(self) -> None:
        """POST without CSRF cookie should be rejected."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = CSRFMiddleware(mock_app)
        scope = create_scope(method="POST", path="/")

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 403
        assert b"CSRF cookie missing" in send.body

    @pytest.mark.asyncio
    async def test_post_without_header_rejected(self) -> None:
        """POST with cookie but without header should be rejected."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = CSRFMiddleware(mock_app)
        scope = create_scope(
            method="POST",
            path="/",
            headers=[(b"cookie", b"csrf_token=abc123")],
        )

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 403
        assert b"CSRF header missing" in send.body

    @pytest.mark.asyncio
    async def test_post_with_mismatched_tokens_rejected(self) -> None:
        """POST with mismatched tokens should be rejected."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = CSRFMiddleware(mock_app)
        scope = create_scope(
            method="POST",
            path="/",
            headers=[
                (b"cookie", b"csrf_token=abc123"),
                (b"x-csrf-token", b"xyz789"),
            ],
        )

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 403
        assert b"CSRF token mismatch" in send.body

    @pytest.mark.asyncio
    async def test_post_with_valid_tokens_allowed(self) -> None:
        """POST with valid matching tokens should be allowed."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = CSRFMiddleware(mock_app)
        token = "valid_token_123"
        scope = create_scope(
            method="POST",
            path="/",
            headers=[
                (b"cookie", f"csrf_token={token}".encode()),
                (b"x-csrf-token", token.encode()),
            ],
        )

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_put_request_requires_csrf(self) -> None:
        """PUT request should require CSRF validation."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = CSRFMiddleware(mock_app)
        scope = create_scope(method="PUT", path="/")

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 403

    @pytest.mark.asyncio
    async def test_delete_request_requires_csrf(self) -> None:
        """DELETE request should require CSRF validation."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = CSRFMiddleware(mock_app)
        scope = create_scope(method="DELETE", path="/")

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 403

    @pytest.mark.asyncio
    async def test_patch_request_requires_csrf(self) -> None:
        """PATCH request should require CSRF validation."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = CSRFMiddleware(mock_app)
        scope = create_scope(method="PATCH", path="/")

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 403

    @pytest.mark.asyncio
    async def test_safe_methods_skip_validation(self) -> None:
        """Safe methods should skip CSRF validation."""
        for method in ["GET", "HEAD", "OPTIONS", "TRACE"]:
            messages_sent: list[dict] = []

            async def mock_app(scope, receive, send):
                await send(
                    {"type": "http.response.start", "status": 200, "headers": []}
                )
                await send({"type": "http.response.body", "body": b"OK"})

            async def mock_send(message):
                messages_sent.append(message)

            middleware = CSRFMiddleware(mock_app)
            scope = create_scope(
                method=method,
                path="/",
                headers=[(b"cookie", b"csrf_token=abc123")],
            )

            await middleware(scope, create_noop_receive(), mock_send)

            start_msg = next(
                m for m in messages_sent if m["type"] == "http.response.start"
            )
            assert start_msg["status"] == 200, f"{method} should succeed"


class TestCSRFPathExclusion:
    """Tests for CSRF path exclusion."""

    @pytest.mark.asyncio
    async def test_excluded_path_skipped(self) -> None:
        """Excluded paths should skip CSRF validation."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = CSRFMiddleware(mock_app, exclude_paths=["/webhook", "/api/public"])
        scope = create_scope(method="POST", path="/webhook")

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_excluded_path_prefix(self) -> None:
        """Path prefix exclusion should work."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = CSRFMiddleware(mock_app, exclude_paths=["/webhook"])
        scope = create_scope(method="POST", path="/webhook/github")

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_non_excluded_path_checked(self) -> None:
        """Non-excluded paths should still require CSRF."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = CSRFMiddleware(mock_app, exclude_paths=["/webhook"])
        scope = create_scope(method="POST", path="/api/users")

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 403


class TestCSRFCookieBuilding:
    """Tests for CSRF cookie header building."""

    def test_build_cookie_header_basic(self) -> None:
        """Should build basic cookie header."""
        middleware = CSRFMiddleware(None)
        header = middleware._build_cookie_header("token123")

        key, value = header
        assert key == b"set-cookie"

        cookie_str = value.decode()
        assert "csrf_token=token123" in cookie_str
        assert "Max-Age=86400" in cookie_str
        assert "Path=/" in cookie_str
        assert "SameSite=Lax" in cookie_str

    def test_build_cookie_header_secure(self) -> None:
        """Should include Secure flag when enabled."""
        middleware = CSRFMiddleware(None, cookie_secure=True)
        _, value = middleware._build_cookie_header("token123")

        cookie_str = value.decode()
        assert "Secure" in cookie_str

    def test_build_cookie_header_httponly(self) -> None:
        """Should include HttpOnly flag when enabled."""
        middleware = CSRFMiddleware(None, cookie_httponly=True)
        _, value = middleware._build_cookie_header("token123")

        cookie_str = value.decode()
        assert "HttpOnly" in cookie_str

    def test_build_cookie_header_domain(self) -> None:
        """Should include Domain when specified."""
        middleware = CSRFMiddleware(None, cookie_domain="example.com")
        _, value = middleware._build_cookie_header("token123")

        cookie_str = value.decode()
        assert "Domain=example.com" in cookie_str
