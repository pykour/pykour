import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from pykour.app import ASGIApp
from pykour.types import Scope, Receive, Send


@pytest.fixture
def temp_router_dir():
    """Create a temporary directory for router files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def create_handler():
    """Helper to create handler files."""
    def _create_handler(base_path: str, path: str, method: str, content: str):
        handler_path = Path(base_path) / path
        handler_path.mkdir(parents=True, exist_ok=True)
        handler_file = handler_path / f"{method}.py"
        handler_file.write_text(content)
        return handler_file
    return _create_handler


class TestASGIApp:
    """Test cases for ASGIApp class."""

    @pytest.mark.asyncio
    async def test_basic_get_request(self, temp_router_dir, create_handler):
        """Test basic GET request handling."""
        # Create a simple handler
        create_handler(
            temp_router_dir,
            "users",
            "get",
            """
async def handler(request, response):
    return {"users": ["user1", "user2"]}
"""
        )
        
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/users",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        # Check that response was sent correctly
        assert send.call_count == 2
        start_call = send.call_args_list[0][0][0]
        assert start_call["type"] == "http.response.start"
        assert start_call["status"] == 200  # Default for GET
        
        body_call = send.call_args_list[1][0][0]
        assert body_call["type"] == "http.response.body"
        assert b'{"users": ["user1", "user2"]}' in body_call["body"]

    @pytest.mark.asyncio
    async def test_post_request_default_status(self, temp_router_dir, create_handler):
        """Test POST request with default 201 status."""
        create_handler(
            temp_router_dir,
            "users",
            "post",
            """
async def handler(request, response):
    return {"id": 1, "name": "New User"}
"""
        )
        
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "POST",
            "path": "/users",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        start_call = send.call_args_list[0][0][0]
        assert start_call["status"] == 201  # Default for POST

    @pytest.mark.asyncio
    async def test_delete_request_default_status(self, temp_router_dir, create_handler):
        """Test DELETE request with default 204 status."""
        create_handler(
            temp_router_dir,
            "users",
            "delete",
            """
async def handler(request, response):
    return None
"""
        )
        
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "DELETE",
            "path": "/users",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        start_call = send.call_args_list[0][0][0]
        assert start_call["status"] == 204  # Default for DELETE

    @pytest.mark.asyncio
    async def test_prefix_handling(self, temp_router_dir, create_handler):
        """Test request handling with URL prefix."""
        create_handler(
            temp_router_dir,
            "users",
            "get",
            """
async def handler(request, response):
    return {"api": "v1", "users": []}
"""
        )
        
        app = ASGIApp(prefix="/api/v1", base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/users",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        assert send.call_count == 2
        start_call = send.call_args_list[0][0][0]
        assert start_call["status"] == 200

    @pytest.mark.asyncio
    async def test_nested_path_handling(self, temp_router_dir, create_handler):
        """Test handling of nested paths."""
        create_handler(
            temp_router_dir,
            "api/v1/users",
            "get",
            """
async def handler(request, response):
    return {"nested": True}
"""
        )
        
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/users",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        assert send.call_count == 2
        body_call = send.call_args_list[1][0][0]
        assert b'{"nested": true}' in body_call["body"]

    @pytest.mark.asyncio
    async def test_404_not_found(self, temp_router_dir):
        """Test 404 response for non-existent routes."""
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/nonexistent",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        start_call = send.call_args_list[0][0][0]
        assert start_call["status"] == 404
        
        body_call = send.call_args_list[1][0][0]
        assert b"Not Found" in body_call["body"]

    @pytest.mark.asyncio
    async def test_handler_modifying_response(self, temp_router_dir, create_handler):
        """Test handler modifying response status and headers."""
        create_handler(
            temp_router_dir,
            "custom",
            "get",
            """
async def handler(request, response):
    response.status = 202
    response._headers["X-Custom-Header"] = "CustomValue"
    return {"modified": True}
"""
        )
        
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/custom",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        start_call = send.call_args_list[0][0][0]
        assert start_call["status"] == 202
        
        # Check for custom header
        headers = {k.decode(): v.decode() for k, v in start_call["headers"]}
        assert headers.get("x-custom-header") == "CustomValue"

    @pytest.mark.asyncio
    async def test_error_handling(self, temp_router_dir, create_handler):
        """Test 500 error handling when handler raises exception."""
        create_handler(
            temp_router_dir,
            "error",
            "get",
            """
async def handler(request, response):
    raise ValueError("Something went wrong")
"""
        )
        
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/error",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        start_call = send.call_args_list[0][0][0]
        assert start_call["status"] == 500
        
        body_call = send.call_args_list[1][0][0]
        assert b"Internal Server Error" in body_call["body"]

    @pytest.mark.asyncio
    async def test_handler_without_return(self, temp_router_dir, create_handler):
        """Test handler that doesn't return anything."""
        create_handler(
            temp_router_dir,
            "void",
            "get",
            """
async def handler(request, response):
    response._body = "Set directly"
"""
        )
        
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/void",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        body_call = send.call_args_list[1][0][0]
        assert b"Set directly" in body_call["body"]

    @pytest.mark.asyncio
    async def test_non_http_scope_ignored(self, temp_router_dir):
        """Test that non-HTTP scopes are ignored."""
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "websocket",
            "path": "/ws",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        # Should not call send for non-HTTP requests
        assert send.call_count == 0

    def test_resolve_handler_path(self, temp_router_dir, create_handler):
        """Test handler path resolution logic."""
        # Create the handler files first
        create_handler(temp_router_dir, "users", "get", "async def handler(r, res): pass")
        create_handler(temp_router_dir, "users", "post", "async def handler(r, res): pass")
        create_handler(temp_router_dir, "users/123", "delete", "async def handler(r, res): pass")
        create_handler(temp_router_dir, "", "get", "async def handler(r, res): pass")
        
        app = ASGIApp(prefix="/api/v1", base_path=temp_router_dir)
        
        # Test with prefix
        path = app.resolve_handler_path("GET", "/api/v1/users")
        assert path == Path(temp_router_dir) / "users" / "get.py"
        
        # Test without prefix
        path = app.resolve_handler_path("POST", "/users")
        assert path == Path(temp_router_dir) / "users" / "post.py"
        
        # Test nested path
        path = app.resolve_handler_path("DELETE", "/api/v1/users/123")
        assert path == Path(temp_router_dir) / "users" / "123" / "delete.py"
        
        # Test root path
        app2 = ASGIApp(base_path=temp_router_dir)
        path = app2.resolve_handler_path("GET", "/")
        assert path == Path(temp_router_dir) / "get.py"
        
        # Test non-existent path
        path = app.resolve_handler_path("GET", "/api/v1/nonexistent")
        assert path is None

    @pytest.mark.asyncio
    async def test_alternative_handler_name(self, temp_router_dir, create_handler):
        """Test handler with 'handle' function name instead of 'handler'."""
        create_handler(
            temp_router_dir,
            "alt",
            "get",
            """
async def handle(request, response):
    return {"alternative": "handler"}
"""
        )
        
        app = ASGIApp(base_path=temp_router_dir)
        
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/alt",
            "headers": [],
            "query_string": b"",
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        await app(scope, receive, send)
        
        assert send.call_count == 2
        body_call = send.call_args_list[1][0][0]
        assert b'{"alternative": "handler"}' in body_call["body"]