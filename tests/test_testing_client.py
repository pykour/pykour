"""Tests for the TestClient."""

import json

import pytest

from pykour.testing import TestClient, TestResponse


class TestTestResponse:
    """Tests for TestResponse class."""

    def test_text_property(self) -> None:
        """Should decode body as UTF-8 text."""
        response = TestResponse(
            status_code=200,
            headers={},
            body=b"Hello, World!",
        )
        assert response.text == "Hello, World!"

    def test_json_method(self) -> None:
        """Should parse body as JSON."""
        data = {"name": "Alice", "age": 30}
        response = TestResponse(
            status_code=200,
            headers={"content-type": "application/json"},
            body=json.dumps(data).encode(),
        )
        assert response.json() == data

    def test_json_invalid(self) -> None:
        """Should raise on invalid JSON."""
        response = TestResponse(
            status_code=200,
            headers={},
            body=b"not json",
        )
        with pytest.raises(json.JSONDecodeError):
            response.json()

    def test_is_success(self) -> None:
        """Should identify successful responses."""
        assert TestResponse(200, {}, b"").is_success is True
        assert TestResponse(201, {}, b"").is_success is True
        assert TestResponse(299, {}, b"").is_success is True
        assert TestResponse(300, {}, b"").is_success is False
        assert TestResponse(404, {}, b"").is_success is False

    def test_is_redirect(self) -> None:
        """Should identify redirect responses."""
        assert TestResponse(301, {}, b"").is_redirect is True
        assert TestResponse(302, {}, b"").is_redirect is True
        assert TestResponse(200, {}, b"").is_redirect is False
        assert TestResponse(400, {}, b"").is_redirect is False

    def test_is_client_error(self) -> None:
        """Should identify client error responses."""
        assert TestResponse(400, {}, b"").is_client_error is True
        assert TestResponse(404, {}, b"").is_client_error is True
        assert TestResponse(499, {}, b"").is_client_error is True
        assert TestResponse(500, {}, b"").is_client_error is False
        assert TestResponse(200, {}, b"").is_client_error is False

    def test_is_server_error(self) -> None:
        """Should identify server error responses."""
        assert TestResponse(500, {}, b"").is_server_error is True
        assert TestResponse(503, {}, b"").is_server_error is True
        assert TestResponse(400, {}, b"").is_server_error is False
        assert TestResponse(200, {}, b"").is_server_error is False


class TestTestClientBasic:
    """Basic tests for TestClient."""

    @pytest.mark.asyncio
    async def test_simple_get_request(self) -> None:
        """Should handle simple GET request."""

        async def app(scope, receive, send):
            assert scope["type"] == "http"
            assert scope["method"] == "GET"
            assert scope["path"] == "/test"

            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Hello",
                }
            )

        client = TestClient(app)
        response = await client.get("/test")

        assert response.status_code == 200
        assert response.text == "Hello"
        assert response.headers["content-type"] == "text/plain"

    @pytest.mark.asyncio
    async def test_post_with_json_body(self) -> None:
        """Should handle POST request with JSON body."""
        received_body = None

        async def app(scope, receive, send):
            nonlocal received_body
            assert scope["method"] == "POST"

            # Read body
            message = await receive()
            received_body = json.loads(message["body"])

            await send(
                {
                    "type": "http.response.start",
                    "status": 201,
                    "headers": [],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"Created",
                }
            )

        client = TestClient(app)
        response = await client.post("/users", json={"name": "Alice"})

        assert response.status_code == 201
        assert received_body == {"name": "Alice"}

    @pytest.mark.asyncio
    async def test_query_parameters(self) -> None:
        """Should include query parameters in request."""

        async def app(scope, receive, send):
            assert scope["query_string"] == b"page=1&limit=10"

            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"OK",
                }
            )

        client = TestClient(app)
        response = await client.get("/items", params={"page": 1, "limit": 10})

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_custom_headers(self) -> None:
        """Should include custom headers in request."""
        received_auth = None

        async def app(scope, receive, send):
            nonlocal received_auth
            headers = dict(scope["headers"])
            received_auth = headers.get(b"authorization", b"").decode()

            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"OK",
                }
            )

        client = TestClient(app)
        response = await client.get(
            "/protected",
            headers={"Authorization": "Bearer token123"},
        )

        assert response.status_code == 200
        assert received_auth == "Bearer token123"

    @pytest.mark.asyncio
    async def test_default_headers(self) -> None:
        """Should include default headers in all requests."""
        received_api_key = None

        async def app(scope, receive, send):
            nonlocal received_api_key
            headers = dict(scope["headers"])
            received_api_key = headers.get(b"x-api-key", b"").decode()

            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"OK",
                }
            )

        client = TestClient(app, default_headers={"X-API-Key": "secret"})
        await client.get("/test")

        assert received_api_key == "secret"


class TestTestClientMethods:
    """Tests for different HTTP methods."""

    @pytest.mark.asyncio
    async def test_put_request(self) -> None:
        """Should handle PUT request."""

        async def app(scope, receive, send):
            assert scope["method"] == "PUT"
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send({"type": "http.response.body", "body": b"Updated"})

        client = TestClient(app)
        response = await client.put("/items/1", json={"name": "Updated"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_patch_request(self) -> None:
        """Should handle PATCH request."""

        async def app(scope, receive, send):
            assert scope["method"] == "PATCH"
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send({"type": "http.response.body", "body": b"Patched"})

        client = TestClient(app)
        response = await client.patch("/items/1", json={"name": "Patched"})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_request(self) -> None:
        """Should handle DELETE request."""

        async def app(scope, receive, send):
            assert scope["method"] == "DELETE"
            await send(
                {
                    "type": "http.response.start",
                    "status": 204,
                    "headers": [],
                }
            )
            await send({"type": "http.response.body", "body": b""})

        client = TestClient(app)
        response = await client.delete("/items/1")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_head_request(self) -> None:
        """Should handle HEAD request."""

        async def app(scope, receive, send):
            assert scope["method"] == "HEAD"
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-length", b"100")],
                }
            )
            await send({"type": "http.response.body", "body": b""})

        client = TestClient(app)
        response = await client.head("/items")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_options_request(self) -> None:
        """Should handle OPTIONS request."""

        async def app(scope, receive, send):
            assert scope["method"] == "OPTIONS"
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"allow", b"GET, POST, PUT, DELETE")],
                }
            )
            await send({"type": "http.response.body", "body": b""})

        client = TestClient(app)
        response = await client.options("/items")
        assert response.status_code == 200
        assert response.headers["allow"] == "GET, POST, PUT, DELETE"


class TestTestClientIntegration:
    """Integration tests with Pykour application."""

    @pytest.mark.asyncio
    async def test_with_pykour_app(self, tmp_path) -> None:
        """Should work with actual Pykour application."""
        from pykour import Pykour

        # Create routes directory
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()

        # Create a simple route
        (routes_dir / "route.py").write_text("""
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "Hello from Pykour!"})

async def post(request):
    data = await request.json()
    return JSONResponse({"received": data}, status_code=201)
""")

        app = Pykour(routes_dir=str(routes_dir))
        client = TestClient(app)

        # Test GET
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello from Pykour!"}

        # Test POST
        response = await client.post("/", json={"name": "Test"})
        assert response.status_code == 201
        assert response.json() == {"received": {"name": "Test"}}

    @pytest.mark.asyncio
    async def test_with_path_params(self, tmp_path) -> None:
        """Should work with dynamic path parameters."""
        from pykour import Pykour

        routes_dir = tmp_path / "routes"
        (routes_dir / "users" / "[id]").mkdir(parents=True)

        (routes_dir / "users" / "[id]" / "route.py").write_text("""
from pykour import JSONResponse
from pykour.schema import Path

async def get(id: int = Path()):
    return JSONResponse({"user_id": id})
""")

        app = Pykour(routes_dir=str(routes_dir))
        client = TestClient(app)

        response = await client.get("/users/123")
        assert response.status_code == 200
        assert response.json() == {"user_id": 123}

    @pytest.mark.asyncio
    async def test_error_responses(self, tmp_path) -> None:
        """Should handle error responses."""
        from pykour import Pykour

        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()

        (routes_dir / "route.py").write_text("""
from pykour import JSONResponse

async def get():
    return JSONResponse({"error": "Not found"}, status_code=404)
""")

        app = Pykour(routes_dir=str(routes_dir))
        client = TestClient(app)

        response = await client.get("/")
        assert response.status_code == 404
        assert response.is_client_error is True
        assert response.json() == {"error": "Not found"}

    @pytest.mark.asyncio
    async def test_with_middleware(self, tmp_path) -> None:
        """Should work with middleware."""
        from pykour import Pykour
        from pykour.middleware import CORSMiddleware

        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()

        (routes_dir / "route.py").write_text("""
from pykour import JSONResponse

async def get():
    return JSONResponse({"status": "ok"})
""")

        app = Pykour(routes_dir=str(routes_dir))
        app.add_middleware(CORSMiddleware, allow_origins=["*"])

        client = TestClient(app)

        response = await client.get(
            "/",
            headers={"Origin": "https://example.com"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
