"""Integration tests for @status_code decorator with Pykour app."""

from __future__ import annotations

from pathlib import Path

import pytest

from pykour import Pykour
from pykour.testing import TestClient

# Path to test routes directory
ROUTES_DIR = Path(__file__).parent / "routes"


class TestStatusCodeIntegration:
    """Integration tests for status code application."""

    @pytest.mark.asyncio
    async def test_declarative_status_applied(self) -> None:
        """Test that declarative status code is applied to default response."""
        app = Pykour(routes_dir=ROUTES_DIR / "status_code_test")
        client = TestClient(app)

        response = await client.post("/")
        assert response.status_code == 201
        data = response.json()
        assert data["created"] is True

    @pytest.mark.asyncio
    async def test_explicit_status_takes_precedence(self) -> None:
        """Test that explicit status code in response takes precedence."""
        app = Pykour(routes_dir=ROUTES_DIR / "status_code_test")
        client = TestClient(app)

        # Explicit 404 should override declarative 200
        response = await client.get("/?not_found=true")
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "Not Found"

    @pytest.mark.asyncio
    async def test_default_status_without_decorator(self) -> None:
        """Test that handlers without decorator use default 200."""
        app = Pykour(routes_dir=ROUTES_DIR / "status_code_test")
        client = TestClient(app)

        response = await client.put("/")
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] is True

    @pytest.mark.asyncio
    async def test_declarative_204_applied(self) -> None:
        """Test that declarative 204 status code is applied."""
        app = Pykour(routes_dir=ROUTES_DIR / "status_code_test")
        client = TestClient(app)

        response = await client.delete("/")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_dynamic_override_declarative(self) -> None:
        """Test that dynamic status code overrides declarative."""
        app = Pykour(routes_dir=ROUTES_DIR / "status_code_test")
        client = TestClient(app)

        # Explicit 409 should override declarative 204
        response = await client.delete("/", params={"conflict": "true"})
        assert response.status_code == 409
        data = response.json()
        assert data["error"] == "Conflict"


class TestStatusCodeOpenAPI:
    """Tests for OpenAPI schema generation with @status_code."""

    @pytest.mark.asyncio
    async def test_openapi_reflects_declared_status(self) -> None:
        """Test that OpenAPI schema includes declared status codes."""
        from pykour.openapi.generator import OpenAPIGenerator

        app = Pykour(
            routes_dir=ROUTES_DIR / "status_code_test",
            title="Test API",
            version="1.0.0",
        )

        generator = OpenAPIGenerator(app._router, app._openapi_config)
        schema = generator.generate()

        # Check POST endpoint has 201 response
        post_responses = schema["paths"]["/"]["post"]["responses"]
        assert "201" in post_responses
        assert post_responses["201"]["description"] == "Created"

        # Check GET endpoint has both 200 and 404 responses
        get_responses = schema["paths"]["/"]["get"]["responses"]
        assert "200" in get_responses
        assert "404" in get_responses
        assert get_responses["200"]["description"] == "Success"
        assert get_responses["404"]["description"] == "Not Found"

        # Check DELETE endpoint has 204 response
        delete_responses = schema["paths"]["/"]["delete"]["responses"]
        assert "204" in delete_responses
        assert delete_responses["204"]["description"] == "No Content"

    @pytest.mark.asyncio
    async def test_openapi_default_without_decorator(self) -> None:
        """Test that OpenAPI uses default 200 for handlers without decorator."""
        from pykour.openapi.generator import OpenAPIGenerator

        app = Pykour(
            routes_dir=ROUTES_DIR / "status_code_test",
            title="Test API",
            version="1.0.0",
        )

        generator = OpenAPIGenerator(app._router, app._openapi_config)
        schema = generator.generate()

        # Check PUT endpoint has default 200 response
        put_responses = schema["paths"]["/"]["put"]["responses"]
        assert "200" in put_responses
        assert put_responses["200"]["description"] == "Successful response"


class TestMethodDefaultStatusCode:
    """Integration tests for method-based default status codes (no decorator)."""

    @pytest.mark.asyncio
    async def test_post_returns_201_without_decorator(self) -> None:
        """Test POST returns 201 without @status_code decorator."""
        app = Pykour(routes_dir=ROUTES_DIR / "method_default_test")
        client = TestClient(app)

        response = await client.post("/")
        assert response.status_code == 201
        data = response.json()
        assert data["method"] == "post"

    @pytest.mark.asyncio
    async def test_delete_returns_204_without_decorator(self) -> None:
        """Test DELETE returns 204 without @status_code decorator."""
        app = Pykour(routes_dir=ROUTES_DIR / "method_default_test")
        client = TestClient(app)

        response = await client.delete("/")
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_get_returns_200_without_decorator(self) -> None:
        """Test GET returns 200 without @status_code decorator."""
        app = Pykour(routes_dir=ROUTES_DIR / "method_default_test")
        client = TestClient(app)

        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "get"

    @pytest.mark.asyncio
    async def test_put_returns_200_without_decorator(self) -> None:
        """Test PUT returns 200 without @status_code decorator."""
        app = Pykour(routes_dir=ROUTES_DIR / "method_default_test")
        client = TestClient(app)

        response = await client.put("/")
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "put"

    @pytest.mark.asyncio
    async def test_patch_returns_200_without_decorator(self) -> None:
        """Test PATCH returns 200 without @status_code decorator."""
        app = Pykour(routes_dir=ROUTES_DIR / "method_default_test")
        client = TestClient(app)

        response = await client.patch("/")
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "patch"
