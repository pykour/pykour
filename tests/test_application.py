"""Tests for pykour.application module."""

import json
from pathlib import Path

from pykour import Pykour
from pykour.types import Message, Scope

from tests.conftest import MockSend, create_receive, create_scope


ROUTES_DIR = Path(__file__).parent / "routes"


class TestPykourRouting:
    """Test Pykour file-based routing functionality."""

    async def test_root_route(self) -> None:
        """Root route should be accessible."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        assert json.loads(send.body) == {"message": "Hello, Pykour!"}

    async def test_static_route_get(self) -> None:
        """GET /api/users should return users."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/api/users")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        data = json.loads(send.body)
        assert "users" in data

    async def test_static_route_post(self) -> None:
        """POST /api/users should create user."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="POST", path="/api/users")
        receive = create_receive(body=b'{"name": "Bob"}')
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 201
        data = json.loads(send.body)
        assert data["created"] is True

    async def test_dynamic_route_get(self) -> None:
        """GET /api/users/123 should return user with ID."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/api/users/123")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        data = json.loads(send.body)
        assert data["id"] == "123"

    async def test_dynamic_route_put(self) -> None:
        """PUT /api/users/456 should update user."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="PUT", path="/api/users/456")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        data = json.loads(send.body)
        assert data["id"] == "456"
        assert data["updated"] is True

    async def test_dynamic_route_delete(self) -> None:
        """DELETE /api/users/789 should delete user with 204 status and empty body.

        Per RFC 7231, 204 No Content responses MUST NOT include a body.
        """
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="DELETE", path="/api/users/789")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 204
        # RFC 7231: 204 No Content MUST have empty body
        assert send.body == b""


class TestPykourErrorHandling:
    """Test Pykour error handling."""

    async def test_not_found(self) -> None:
        """Unknown path should return 404."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="GET", path="/unknown")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 404
        assert json.loads(send.body) == {"error": "Not Found"}

    async def test_method_not_allowed(self) -> None:
        """Wrong method should return 405 with Allow header."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(method="DELETE", path="/api/users")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 405
        assert json.loads(send.body) == {"error": "Method Not Allowed"}
        # RFC 7231: 405 response MUST include Allow header
        allow_header = send.headers.get(b"Allow", b"").decode()
        allowed_methods = {m.strip() for m in allow_header.split(",")}
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods

    async def test_missing_required_parameter(self) -> None:
        """Missing required parameter should return 422 with error details."""
        app = Pykour(routes_dir=ROUTES_DIR)

        # /api/required has a handler that requires 'required_param'
        scope = create_scope(method="GET", path="/api/required")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 422
        data = json.loads(send.body)
        assert data["error"] == "Validation Error"
        assert "detail" in data
        assert len(data["detail"]) == 1
        error = data["detail"][0]
        assert error["loc"] == ["parameter", "required_param"]
        assert "required_param" in error["msg"]
        assert error["type"] == "value_error.missing"

    async def test_required_parameter_provided(self) -> None:
        """Required parameter provided via query string should work."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope = create_scope(
            method="GET",
            path="/api/required",
            query_string=b"required_param=test_value",
        )
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        data = json.loads(send.body)
        assert data["param"] == "test_value"


class TestPykourNonHttp:
    """Test non-HTTP scope handling."""

    async def test_websocket_scope_handled(self) -> None:
        """WebSocket scope should be handled (close with 4004 if no handler)."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope: Scope = {"type": "websocket", "path": "/ws"}
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        # WebSocket without handler should close with 4004 (Not Found)
        assert len(send.messages) == 1
        assert send.messages[0]["type"] == "websocket.close"
        assert send.messages[0]["code"] == 4004

    async def test_lifespan_scope_handled(self) -> None:
        """Lifespan scope should be handled correctly."""
        app = Pykour(routes_dir=ROUTES_DIR)

        scope: Scope = {"type": "lifespan"}
        messages_to_send = [
            {"type": "lifespan.startup"},
            {"type": "lifespan.shutdown"},
        ]
        message_index = 0

        async def lifespan_receive() -> Message:
            nonlocal message_index
            msg = messages_to_send[message_index]
            message_index += 1
            return msg

        send = MockSend()

        await app(scope, lifespan_receive, send)

        # Should receive startup.complete and shutdown.complete
        assert len(send.messages) == 2
        assert send.messages[0]["type"] == "lifespan.startup.complete"
        assert send.messages[1]["type"] == "lifespan.shutdown.complete"


class TestPykourConcurrency:
    """Test concurrent request handling."""

    async def test_concurrent_startup_race_condition(self) -> None:
        """Concurrent requests should not cause startup race condition."""
        import asyncio
        from unittest.mock import patch

        app = Pykour(routes_dir=ROUTES_DIR)
        startup_count = 0
        original_build = app._build_middleware_stack

        def counting_build() -> None:
            nonlocal startup_count
            startup_count += 1
            return original_build()

        # Simulate concurrent requests triggering auto-start
        async def make_request() -> int:
            scope = create_scope(method="GET", path="/")
            receive = create_receive()
            send = MockSend()
            await app(scope, receive, send)
            return send.status

        with patch.object(app, "_build_middleware_stack", counting_build):
            # Launch multiple concurrent requests
            results = await asyncio.gather(*[make_request() for _ in range(10)])

        # All requests should succeed
        assert all(status == 200 for status in results)
        # Middleware stack should only be built once
        assert startup_count == 1
