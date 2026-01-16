"""Tests for HEAD and OPTIONS HTTP method support."""

from __future__ import annotations

from pathlib import Path

import pytest

from pykour import Pykour
from pykour.router import Router
from pykour.testing import TestClient

# Path to test routes directory
ROUTES_DIR = Path(__file__).parent / "routes"


class TestHeadMethod:
    """Tests for HEAD HTTP method support."""

    @pytest.mark.asyncio
    async def test_head_auto_from_get(self) -> None:
        """HEAD should return headers from GET handler with empty body."""
        app = Pykour(routes_dir=ROUTES_DIR)
        client = TestClient(app)

        response = await client.head("/api/users")
        assert response.status_code == 200
        assert response.body == b""
        # Headers should still be present
        assert "content-type" in response.headers

    @pytest.mark.asyncio
    async def test_head_explicit_handler(self) -> None:
        """Explicit HEAD handler should be used when defined."""
        app = Pykour(routes_dir=ROUTES_DIR / "head_test")
        client = TestClient(app)

        response = await client.head("/")
        assert response.status_code == 200
        assert response.body == b""

    @pytest.mark.asyncio
    async def test_head_no_get_handler_returns_405(self) -> None:
        """HEAD should return 405 if no GET or HEAD handler exists."""
        app = Pykour(routes_dir=ROUTES_DIR)
        client = TestClient(app)

        # /api/body only has POST handler
        response = await client.head("/api/body")
        assert response.status_code == 405
        assert "allow" in response.headers

    @pytest.mark.asyncio
    async def test_head_preserves_content_length(self) -> None:
        """HEAD response should preserve Content-Length from GET response."""
        app = Pykour(routes_dir=ROUTES_DIR)
        client = TestClient(app)

        # HEAD should have empty body but still contain content-type header
        head_response = await client.head("/api/users")
        assert head_response.body == b""
        assert head_response.status_code == 200


class TestOptionsMethod:
    """Tests for OPTIONS HTTP method support."""

    @pytest.mark.asyncio
    async def test_options_explicit_handler(self) -> None:
        """Explicit OPTIONS handler should be called."""
        app = Pykour(routes_dir=ROUTES_DIR / "options_test")
        client = TestClient(app)

        response = await client.options("/")
        assert response.status_code == 200
        data = response.json()
        assert data["custom"] == "options handler"

    @pytest.mark.asyncio
    async def test_options_no_handler_returns_405(self) -> None:
        """OPTIONS without handler returns 405 (without CORS middleware)."""
        app = Pykour(routes_dir=ROUTES_DIR)
        client = TestClient(app)

        response = await client.options("/api/users")
        # Without CORS middleware, OPTIONS returns 405
        # because there's no explicit OPTIONS handler
        assert response.status_code == 405


class TestAllowedMethods:
    """Tests for get_allowed_methods() functionality."""

    def test_get_allowed_methods_includes_head(self) -> None:
        """Allowed methods should include HEAD when GET is available."""
        router = Router(ROUTES_DIR)
        methods = router.get_allowed_methods("/api/users")

        assert "GET" in methods
        assert "HEAD" in methods
        assert "POST" in methods

    def test_get_allowed_methods_no_head_without_get(self) -> None:
        """HEAD should not be included when GET is not available."""
        router = Router(ROUTES_DIR)
        methods = router.get_allowed_methods("/api/body")

        # /api/body only has POST handler
        assert "POST" in methods
        assert "GET" not in methods
        assert "HEAD" not in methods


class TestHttpMethodsConstant:
    """Tests for HTTP_METHODS constant."""

    def test_http_methods_includes_head_and_options(self) -> None:
        """HTTP_METHODS should include head and options."""
        from pykour.router import HTTP_METHODS

        assert "head" in HTTP_METHODS
        assert "options" in HTTP_METHODS
        assert "get" in HTTP_METHODS
        assert "post" in HTTP_METHODS
        assert "put" in HTTP_METHODS
        assert "delete" in HTTP_METHODS
        assert "patch" in HTTP_METHODS
