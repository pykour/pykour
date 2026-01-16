"""Tests for JWT authentication middleware."""

import time

import pytest

from tests.helpers import create_noop_receive, create_noop_send
from pykour import Pykour
from pykour.middleware.auth import JWTAuthMiddleware, create_jwt_token
from pykour.request import State


class TestStateClass:
    """Tests for State class."""

    def test_state_set_and_get_attribute(self) -> None:
        """State should allow setting and getting attributes."""
        state = State()
        state.user = {"id": 123}
        assert state.user == {"id": 123}

    def test_state_multiple_attributes(self) -> None:
        """State should support multiple attributes."""
        state = State()
        state.user = {"id": 123}
        state.token = "abc123"
        state.authenticated = True
        assert state.user == {"id": 123}
        assert state.token == "abc123"
        assert state.authenticated is True

    def test_state_missing_attribute_raises_error(self) -> None:
        """Accessing missing attribute should raise AttributeError."""
        state = State()
        with pytest.raises(AttributeError, match="has no attribute"):
            _ = state.nonexistent

    def test_state_delete_attribute(self) -> None:
        """State should support deleting attributes."""
        state = State()
        state.user = {"id": 123}
        del state.user
        with pytest.raises(AttributeError):
            _ = state.user

    def test_state_delete_missing_attribute_raises_error(self) -> None:
        """Deleting missing attribute should raise AttributeError."""
        state = State()
        with pytest.raises(AttributeError, match="has no attribute"):
            del state.nonexistent


class TestCreateJWTToken:
    """Tests for create_jwt_token helper function."""

    def test_create_basic_token(self) -> None:
        """Basic token creation should work."""
        token = create_jwt_token({"sub": "user123"}, "secret")
        assert isinstance(token, str)
        assert token.count(".") == 2

    def test_create_token_with_expiration(self) -> None:
        """Token with expiration should include exp claim."""
        token = create_jwt_token(
            {"sub": "user123"},
            "secret",
            expires_in=3600,
        )
        # Verify token is valid by decoding (indirectly)
        middleware = JWTAuthMiddleware(None, secret_key="secret")
        payload = middleware._verify_token(token)
        assert payload is not None
        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_create_token_unsupported_algorithm(self) -> None:
        """Unsupported algorithm should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            create_jwt_token({"sub": "user123"}, "secret", algorithm="RS256")


class TestJWTAuthMiddlewareConfig:
    """Tests for JWT middleware configuration."""

    def test_default_config(self) -> None:
        """Default configuration should have sensible defaults."""
        middleware = JWTAuthMiddleware(None, secret_key="secret")
        assert middleware.secret_key == "secret"
        assert middleware.algorithm == "HS256"
        assert middleware.exclude_paths == []
        assert middleware.auto_error is True

    def test_custom_config(self) -> None:
        """Custom configuration should be respected."""
        middleware = JWTAuthMiddleware(
            None,
            secret_key="my-secret",
            algorithm="HS256",
            exclude_paths=["/health", "/login"],
            auto_error=False,
        )
        assert middleware.secret_key == "my-secret"
        assert middleware.exclude_paths == ["/health", "/login"]
        assert middleware.auto_error is False

    def test_unsupported_algorithm_raises_error(self) -> None:
        """Unsupported algorithm should raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            JWTAuthMiddleware(None, secret_key="secret", algorithm="RS256")


class TestJWTTokenVerification:
    """Tests for JWT token verification."""

    def test_valid_token_verification(self) -> None:
        """Valid token should be verified successfully."""
        secret = "test-secret"
        token = create_jwt_token({"sub": "user123", "name": "John"}, secret)
        middleware = JWTAuthMiddleware(None, secret_key=secret)
        payload = middleware._verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["name"] == "John"

    def test_invalid_signature_rejection(self) -> None:
        """Token with invalid signature should be rejected."""
        token = create_jwt_token({"sub": "user123"}, "secret1")
        middleware = JWTAuthMiddleware(None, secret_key="secret2")
        payload = middleware._verify_token(token)
        assert payload is None

    def test_expired_token_rejection(self) -> None:
        """Expired token should be rejected."""
        secret = "test-secret"
        token = create_jwt_token(
            {"sub": "user123"},
            secret,
            expires_in=-10,  # Already expired
        )
        middleware = JWTAuthMiddleware(None, secret_key=secret)
        payload = middleware._verify_token(token)
        assert payload is None

    def test_invalid_token_format(self) -> None:
        """Invalid token format should be rejected."""
        middleware = JWTAuthMiddleware(None, secret_key="secret")
        assert middleware._verify_token("invalid") is None
        assert middleware._verify_token("a.b") is None
        assert middleware._verify_token("a.b.c.d") is None
        assert middleware._verify_token("") is None

    def test_malformed_base64_rejection(self) -> None:
        """Malformed base64 token should be rejected."""
        middleware = JWTAuthMiddleware(None, secret_key="secret")
        assert middleware._verify_token("!!!.@@@.###") is None


class TestJWTTokenExtraction:
    """Tests for JWT token extraction from headers.

    Note: Tests use the shared extract_bearer_token utility from middleware.utils.
    """

    def test_extract_bearer_token(self) -> None:
        """Bearer token should be extracted from Authorization header."""
        from pykour.middleware.utils import extract_bearer_token

        scope = {"headers": [(b"authorization", b"Bearer test-token-123")]}
        token = extract_bearer_token(scope)
        assert token == "test-token-123"

    def test_missing_authorization_header(self) -> None:
        """Missing Authorization header should return None."""
        from pykour.middleware.utils import extract_bearer_token

        scope: dict = {"headers": []}
        token = extract_bearer_token(scope)
        assert token is None

    def test_non_bearer_authorization(self) -> None:
        """Non-Bearer authorization should return None."""
        from pykour.middleware.utils import extract_bearer_token

        scope = {"headers": [(b"authorization", b"Basic dXNlcjpwYXNz")]}
        token = extract_bearer_token(scope)
        assert token is None


class TestJWTPathExclusion:
    """Tests for path exclusion from authentication.

    Note: Tests use the shared is_path_excluded utility from middleware.utils.
    """

    def test_exact_path_excluded(self) -> None:
        """Exact path match should be excluded."""
        from pykour.middleware.utils import is_path_excluded

        exclude_paths = ["/health", "/login"]
        assert is_path_excluded("/health", exclude_paths) is True
        assert is_path_excluded("/login", exclude_paths) is True
        assert is_path_excluded("/api", exclude_paths) is False

    def test_path_prefix_excluded(self) -> None:
        """Paths with excluded prefix should be excluded."""
        from pykour.middleware.utils import is_path_excluded

        exclude_paths = ["/public"]
        assert is_path_excluded("/public", exclude_paths) is True
        assert is_path_excluded("/public/assets", exclude_paths) is True
        assert is_path_excluded("/public/images/logo.png", exclude_paths) is True
        assert is_path_excluded("/publicdata", exclude_paths) is False


class TestJWTAuthMiddlewareIntegration:
    """Integration tests for JWT authentication middleware."""

    @pytest.mark.asyncio
    async def test_authenticated_request(self, tmp_path) -> None:
        """Authenticated request should pass through with user data."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse, Request

async def get(request: Request):
    user = request.state.user
    return JSONResponse({"user_id": user["sub"]})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        secret = "test-secret"
        app.add_middleware(JWTAuthMiddleware, secret_key=secret)

        token = create_jwt_token({"sub": "user123"}, secret)
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
            "headers": [(b"authorization", f"Bearer {token}".encode())],
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        assert start_message["status"] == 200

        body_message = next(
            m for m in received_messages if m["type"] == "http.response.body"
        )
        import json

        body = json.loads(body_message["body"])
        assert body["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_unauthenticated_request_rejected(self, tmp_path) -> None:
        """Request without token should be rejected with 401."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "protected"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(JWTAuthMiddleware, secret_key="secret")

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
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        assert start_message["status"] == 401

        headers_dict = {
            k.decode().lower(): v.decode() for k, v in start_message["headers"]
        }
        assert "www-authenticate" in headers_dict
        assert headers_dict["www-authenticate"] == "Bearer"

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, tmp_path) -> None:
        """Request with invalid token should be rejected with 401."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "protected"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(JWTAuthMiddleware, secret_key="secret")

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
            "headers": [(b"authorization", b"Bearer invalid-token")],
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        assert start_message["status"] == 401

    @pytest.mark.asyncio
    async def test_excluded_path_bypasses_auth(self, tmp_path) -> None:
        """Request to excluded path should bypass authentication."""
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
            JWTAuthMiddleware,
            secret_key="secret",
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
            "headers": [],  # No authorization header
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        assert start_message["status"] == 200

    @pytest.mark.asyncio
    async def test_auto_error_false_continues_without_user(self, tmp_path) -> None:
        """With auto_error=False, request should continue without user data."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse, Request

async def get(request: Request):
    try:
        user = request.state.user
        return JSONResponse({"user_id": user["sub"]})
    except AttributeError:
        return JSONResponse({"user_id": None})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(
            JWTAuthMiddleware,
            secret_key="secret",
            auto_error=False,
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
            "headers": [],  # No authorization header
        }

        await app(scope, receive, send)

        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        assert start_message["status"] == 200

        body_message = next(
            m for m in received_messages if m["type"] == "http.response.body"
        )
        import json

        body = json.loads(body_message["body"])
        assert body["user_id"] is None

    @pytest.mark.asyncio
    async def test_non_http_requests_pass_through(self) -> None:
        """Non-HTTP requests should pass through without authentication."""
        called = False

        async def mock_app(scope, receive, send) -> None:
            nonlocal called
            called = True

        middleware = JWTAuthMiddleware(mock_app, secret_key="secret")
        await middleware(
            {"type": "websocket"}, create_noop_receive(), create_noop_send()
        )

        assert called is True


class TestJWTAuthMiddlewareImport:
    """Tests for JWT middleware import."""

    def test_import_from_package(self) -> None:
        """JWTAuthMiddleware can be imported from pykour.middleware."""
        from pykour.middleware import JWTAuthMiddleware

        assert JWTAuthMiddleware is not None

    def test_import_from_module(self) -> None:
        """JWTAuthMiddleware can be imported from pykour.middleware.auth."""
        from pykour.middleware.auth import JWTAuthMiddleware

        assert JWTAuthMiddleware is not None

    def test_import_create_jwt_token(self) -> None:
        """create_jwt_token can be imported from pykour.middleware."""
        from pykour.middleware import create_jwt_token

        assert create_jwt_token is not None
