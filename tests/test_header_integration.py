"""Integration tests for @header decorator with Pykour app."""

from __future__ import annotations

from pathlib import Path

import pytest

from pykour import Pykour
from pykour.testing import TestClient

# Path to test routes directory
ROUTES_DIR = Path(__file__).parent / "routes"


class TestHeaderIntegration:
    """Integration tests for header application."""

    @pytest.mark.asyncio
    async def test_static_header_applied(self) -> None:
        """Test static header is added to response."""
        app = Pykour(routes_dir=ROUTES_DIR / "header_test")
        client = TestClient(app)

        response = await client.get("/")
        assert response.status_code == 200
        # Headers are lowercased in ASGI
        assert response.headers.get("x-api-version") == "1.0"

    @pytest.mark.asyncio
    async def test_dynamic_header_from_response_body(self) -> None:
        """Test header with response body interpolation."""
        app = Pykour(routes_dir=ROUTES_DIR / "header_test")
        client = TestClient(app)

        response = await client.post("/")
        assert response.status_code == 201
        # Headers are lowercased in ASGI
        assert response.headers.get("location") == "/users/123"
        data = response.json()
        assert data["id"] == 123

    @pytest.mark.asyncio
    async def test_no_header_decorator(self) -> None:
        """Test handler without @header decorator has no extra headers."""
        app = Pykour(routes_dir=ROUTES_DIR / "header_test")
        client = TestClient(app)

        response = await client.put("/")
        assert response.status_code == 200
        # Should not have x-api-version (from GET) or location (from POST)
        assert response.headers.get("x-api-version") is None
        assert response.headers.get("location") is None

    @pytest.mark.asyncio
    async def test_conditional_header_applied(self) -> None:
        """Test conditional header is applied on matching status."""
        app = Pykour(routes_dir=ROUTES_DIR / "header_test")
        client = TestClient(app)

        response = await client.delete("/")
        assert response.status_code == 204
        # Headers are lowercased in ASGI
        assert response.headers.get("x-deleted") == "true"

    @pytest.mark.asyncio
    async def test_dynamic_header_from_path_param(self) -> None:
        """Test header with path parameter interpolation."""
        app = Pykour(routes_dir=ROUTES_DIR / "header_test")
        client = TestClient(app)

        response = await client.get("/users/456")
        assert response.status_code == 200
        # Headers are lowercased in ASGI
        assert response.headers.get("x-user-id") == "456"
        data = response.json()
        assert data["user_id"] == 456

    @pytest.mark.asyncio
    async def test_multiple_headers_stacked(self) -> None:
        """Test multiple @header decorators on same handler."""
        app = Pykour(routes_dir=ROUTES_DIR / "header_test")
        client = TestClient(app)

        response = await client.post("/users/789")
        assert response.status_code == 201
        # Headers are lowercased in ASGI
        assert response.headers.get("location") == "/users/789/profile"
        assert response.headers.get("x-user-id") == "789"


class TestHeaderWithConstructor:
    """Tests for headers set via Response constructor."""

    @pytest.mark.asyncio
    async def test_explicit_header_in_constructor(self) -> None:
        """Test explicit headers in Response constructor work."""
        from pykour import JSONResponse
        from pykour.header import header, get_header_info

        @header("X-Decorator", "decorator-value")
        async def handler() -> JSONResponse:
            return JSONResponse(
                {"data": "test"},
                headers={"X-Constructor": "constructor-value"},
            )

        # Both headers should be present in the final response
        infos = get_header_info(handler)
        assert len(infos) == 1
        assert infos[0].name == "X-Decorator"

        response = await handler()
        assert response.get_header("X-Constructor") == "constructor-value"


class TestHeaderEdgeCases:
    """Edge case tests for header handling."""

    @pytest.mark.asyncio
    async def test_header_with_nested_json_path(self) -> None:
        """Test header interpolation with nested JSON path."""
        from pykour import JSONResponse
        from pykour.header import header
        from pykour.application import Pykour

        @header("X-Nested", "{user.name}")
        async def handler() -> JSONResponse:
            return JSONResponse({"user": {"name": "Alice", "id": 1}})

        # Create a minimal app to test interpolation
        app = Pykour(routes_dir="tests/routes")
        from pykour.router import TrieNode

        app._router._root = TrieNode()
        app._router._routes_cache = None
        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test")
        assert response.status_code == 200
        # Headers are lowercased in ASGI
        assert response.headers.get("x-nested") == "Alice"

    @pytest.mark.asyncio
    async def test_header_with_missing_param_not_applied(self) -> None:
        """Test header is not applied when param cannot be resolved."""
        from pykour import JSONResponse
        from pykour.header import header
        from pykour.application import Pykour

        @header("X-Missing", "{nonexistent}")
        async def handler() -> JSONResponse:
            return JSONResponse({"data": "test"})

        app = Pykour(routes_dir="tests/routes")
        from pykour.router import TrieNode

        app._router._root = TrieNode()
        app._router._routes_cache = None
        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test")
        assert response.status_code == 200
        # Header should not be applied because param couldn't be resolved
        assert response.headers.get("X-Missing") is None
