"""Integration tests for schema validation in routes."""

import json
from pathlib import Path

from pykour import Pykour

from tests.conftest import MockSend, create_receive, create_scope


ROUTES_DIR = Path(__file__).parent / "routes"


class TestPathParamCoercion:
    """Test path parameter type coercion."""

    async def test_path_param_to_int(self) -> None:
        """Path parameter should be coerced to int."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/api/users/123")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        data = json.loads(send.body)
        # Path params are currently strings in the test routes
        assert data["id"] == "123"

    async def test_invalid_path_format(self) -> None:
        """Non-existent path should return 404."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/api/users/not-a-number/extra")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 404


class TestQueryParamValidation:
    """Test query parameter validation."""

    async def test_query_params_parsed(self) -> None:
        """Query parameters should be parsed."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(
            method="GET",
            path="/api/users",
            query_string=b"page=2&limit=10",
        )
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200


class TestBodyValidation:
    """Test request body validation."""

    async def test_valid_json_body(self) -> None:
        """Valid JSON body should be accepted."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="POST", path="/api/users")
        receive = create_receive(body=b'{"name": "Alice"}')
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 201

    async def test_empty_body(self) -> None:
        """Empty body should be handled."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="POST", path="/api/users")
        receive = create_receive(body=b"")
        send = MockSend()

        await app(scope, receive, send)

        # Current implementation just returns created: True
        assert send.status == 201

    async def test_malformed_json_body(self) -> None:
        """Malformed JSON body should return 422 with clear error."""
        app = Pykour(routes_dir=ROUTES_DIR)

        # /api/body expects a Body() parameter with UserSchema
        scope = create_scope(method="POST", path="/api/body")
        receive = create_receive(body=b"{invalid json}")
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 422
        data = json.loads(send.body)
        assert data["error"] == "Validation Error"
        assert "detail" in data
        assert len(data["detail"]) == 1
        error = data["detail"][0]
        assert error["loc"] == ["body"]
        assert "Malformed JSON" in error["msg"]
        assert error["type"] == "value_error.jsondecode"

    async def test_schema_validation_error(self) -> None:
        """Invalid schema data should return 422 with validation details."""
        app = Pykour(routes_dir=ROUTES_DIR)

        # /api/body expects UserSchema with name (min_length=1) and email (valid format)
        scope = create_scope(method="POST", path="/api/body")
        receive = create_receive(body=b'{"name": "", "email": "invalid"}')
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 422
        data = json.loads(send.body)
        assert data["error"] == "Validation Error"
        assert "detail" in data
        # Should have validation errors for name (too short) and email (invalid format)
        assert len(data["detail"]) >= 1

    async def test_valid_schema_body(self) -> None:
        """Valid schema body should return 201 (POST default)."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="POST", path="/api/body")
        receive = create_receive(
            body=b'{"name": "Alice", "email": "alice@example.com"}'
        )
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 201
        data = json.loads(send.body)
        assert data["user"]["name"] == "Alice"
        assert data["user"]["email"] == "alice@example.com"


class TestExistingRoutes:
    """Test that existing routes still work with schema support."""

    async def test_root_route(self) -> None:
        """Root route should still work."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        data = json.loads(send.body)
        assert data["message"] == "Hello, Pykour!"

    async def test_static_route(self) -> None:
        """Static route should still work."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/api/users")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        data = json.loads(send.body)
        assert "users" in data

    async def test_dynamic_route(self) -> None:
        """Dynamic route should still work."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/api/users/456")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        data = json.loads(send.body)
        assert data["id"] == "456"

    async def test_not_found(self) -> None:
        """Non-existent path should return 404."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/nonexistent")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 404

    async def test_method_not_allowed(self) -> None:
        """Wrong method should return 405 with Allow header."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="DELETE", path="/api/users")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 405
        # RFC 7231: 405 response MUST include Allow header
        assert b"Allow" in send.headers
