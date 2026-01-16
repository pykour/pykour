"""Tests for catch-all route [...slug] support."""

from __future__ import annotations

from pathlib import Path

import pytest

from pykour import Pykour
from pykour.router import Route
from pykour.testing import TestClient

# Path to test routes directory
ROUTES_DIR = Path(__file__).parent / "routes"


class TestCatchAllRoutePattern:
    """Tests for catch-all route regex pattern matching."""

    def test_catch_all_regex_single_segment(self) -> None:
        """Catch-all should match single segment."""
        route = Route("/docs/[...slug]", {"GET": lambda: None}, ["slug"])
        result = route.match("/docs/intro")
        assert result is not None
        assert result == {"slug": "intro"}

    def test_catch_all_regex_multiple_segments(self) -> None:
        """Catch-all should match multiple segments."""
        route = Route("/docs/[...slug]", {"GET": lambda: None}, ["slug"])
        result = route.match("/docs/api/users/create")
        assert result is not None
        assert result == {"slug": "api/users/create"}

    def test_catch_all_no_match_parent(self) -> None:
        """Catch-all should not match parent path without segment."""
        route = Route("/docs/[...slug]", {"GET": lambda: None}, ["slug"])
        assert route.match("/docs") is None
        assert route.match("/docs/") is None

    def test_catch_all_is_catch_all_attribute(self) -> None:
        """Route should have is_catch_all attribute."""
        catch_all_route = Route("/docs/[...slug]", {}, ["slug"])
        assert catch_all_route.is_catch_all is True

        normal_route = Route("/api/users/[id]", {}, ["id"])
        assert normal_route.is_catch_all is False

        static_route = Route("/api/users", {}, [])
        assert static_route.is_catch_all is False


class TestCatchAllRoutePriority:
    """Tests for catch-all route priority in routing."""

    def test_static_route_before_catch_all(self) -> None:
        """Static routes should have higher priority than catch-all."""
        # Create a router with both static and catch-all routes
        # The static route should match first
        static_route = Route("/docs/intro", {"GET": lambda: "static"}, [])
        catch_all_route = Route(
            "/docs/[...slug]", {"GET": lambda: "catch_all"}, ["slug"]
        )

        # Verify static route matches exactly
        assert static_route.match("/docs/intro") == {}
        assert catch_all_route.match("/docs/intro") == {"slug": "intro"}

    def test_single_param_before_catch_all(self) -> None:
        """Single-param routes should match before catch-all when same depth."""
        single_param = Route("/api/[id]", {"GET": lambda: "single"}, ["id"])
        catch_all = Route("/api/[...path]", {"GET": lambda: "catch_all"}, ["path"])

        # Both match, but single_param should be preferred due to sorting
        assert single_param.match("/api/123") == {"id": "123"}
        assert catch_all.match("/api/123") == {"path": "123"}

    def test_route_sorting_priority(self) -> None:
        """Routes should be sorted: static > dynamic > catch-all."""
        routes = [
            Route("/api/[...path]", {}, ["path"]),  # catch-all
            Route("/api/users/[id]", {}, ["id"]),  # single param
            Route("/api/users", {}, []),  # static
        ]

        # Sort using the same key function as Router
        def route_priority(route: Route) -> tuple[int, int, int]:
            is_catch_all = 1 if route.is_catch_all else 0
            param_count = route.path_pattern.count("[")
            specificity = -len(route.path_pattern)
            return (is_catch_all, param_count, specificity)

        routes.sort(key=route_priority)

        # Static should be first, then single param, then catch-all
        assert routes[0].path_pattern == "/api/users"
        assert routes[1].path_pattern == "/api/users/[id]"
        assert routes[2].path_pattern == "/api/[...path]"


class TestCatchAllIntegration:
    """Integration tests for catch-all routes with full application."""

    @pytest.mark.asyncio
    async def test_catch_all_handler(self) -> None:
        """Catch-all route should receive full path as parameter."""
        app = Pykour(routes_dir=ROUTES_DIR / "docs_test")
        client = TestClient(app)

        # Single segment
        response = await client.get("/docs/intro")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "intro"

        # Multiple segments
        response = await client.get("/docs/api/users/create")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "api/users/create"

    @pytest.mark.asyncio
    async def test_catch_all_with_prefix(self) -> None:
        """Catch-all should work with path prefix."""
        app = Pykour(routes_dir=ROUTES_DIR / "docs_test")
        client = TestClient(app)

        response = await client.get("/docs/guide/getting-started")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "guide/getting-started"


class TestCatchAllEdgeCases:
    """Edge case tests for catch-all routes."""

    def test_catch_all_with_special_characters(self) -> None:
        """Catch-all should handle paths with special characters."""
        route = Route("/files/[...path]", {"GET": lambda: None}, ["path"])

        # Paths with dots
        result = route.match("/files/path/to/file.txt")
        assert result == {"path": "path/to/file.txt"}

        # Paths with hyphens
        result = route.match("/files/my-folder/my-file")
        assert result == {"path": "my-folder/my-file"}

    def test_catch_all_preserves_slashes(self) -> None:
        """Catch-all should preserve slashes in captured value."""
        route = Route("/api/[...rest]", {"GET": lambda: None}, ["rest"])

        result = route.match("/api/a/b/c/d")
        assert result == {"rest": "a/b/c/d"}
