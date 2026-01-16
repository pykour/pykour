"""Tests for pykour.router module."""

from pathlib import Path

from pykour.router import Route, Router


ROUTES_DIR = Path(__file__).parent / "routes"


class TestRoute:
    """Test Route class."""

    def test_static_route_match(self) -> None:
        """Static route should match exact path."""
        route = Route("/api/users", {"GET": lambda r: None}, [])
        assert route.match("/api/users") == {}
        assert route.match("/api/posts") is None

    def test_dynamic_route_match(self) -> None:
        """Dynamic route should extract parameters."""
        route = Route("/api/users/[id]", {"GET": lambda r: None}, ["id"])
        result = route.match("/api/users/123")
        assert result == {"id": "123"}

    def test_dynamic_route_no_match(self) -> None:
        """Dynamic route should not match different structure."""
        route = Route("/api/users/[id]", {"GET": lambda r: None}, ["id"])
        assert route.match("/api/users") is None
        assert route.match("/api/users/123/extra") is None

    def test_multiple_params(self) -> None:
        """Route should extract multiple parameters."""
        route = Route(
            "/api/users/[userId]/posts/[postId]",
            {"GET": lambda r: None},
            ["userId", "postId"],
        )
        result = route.match("/api/users/1/posts/42")
        assert result == {"userId": "1", "postId": "42"}


class TestRouter:
    """Test Router class."""

    def test_discover_routes(self) -> None:
        """Router should discover routes from directory."""
        router = Router(ROUTES_DIR)
        assert len(router.routes) > 0

    def test_match_static_route(self) -> None:
        """Router should match static routes."""
        router = Router(ROUTES_DIR)
        handler, params = router.match("/api/users", "GET")
        assert handler is not None
        assert params == {}

    def test_match_dynamic_route(self) -> None:
        """Router should match dynamic routes and extract params."""
        router = Router(ROUTES_DIR)
        handler, params = router.match("/api/users/123", "GET")
        assert handler is not None
        assert params == {"id": "123"}

    def test_match_different_methods(self) -> None:
        """Router should return different handlers for different methods."""
        router = Router(ROUTES_DIR)

        get_handler, _ = router.match("/api/users/123", "GET")
        put_handler, _ = router.match("/api/users/123", "PUT")
        delete_handler, _ = router.match("/api/users/123", "DELETE")

        assert get_handler is not None
        assert put_handler is not None
        assert delete_handler is not None
        assert get_handler is not put_handler

    def test_no_match_returns_none(self) -> None:
        """Router should return None for non-existent routes."""
        router = Router(ROUTES_DIR)
        handler, params = router.match("/nonexistent", "GET")
        assert handler is None
        assert params == {}

    def test_method_not_found(self) -> None:
        """Router should return None for unsupported method."""
        router = Router(ROUTES_DIR)
        handler, params = router.match("/api/users", "DELETE")
        assert handler is None

    def test_get_allowed_methods(self) -> None:
        """Router should return allowed methods for a path."""
        router = Router(ROUTES_DIR)
        methods = router.get_allowed_methods("/api/users")
        assert "GET" in methods
        assert "POST" in methods

    def test_get_allowed_methods_dynamic(self) -> None:
        """Router should return allowed methods for dynamic path."""
        router = Router(ROUTES_DIR)
        methods = router.get_allowed_methods("/api/users/123")
        assert "GET" in methods
        assert "PUT" in methods
        assert "DELETE" in methods

    def test_empty_routes_dir(self) -> None:
        """Router should handle non-existent directory."""
        router = Router("/nonexistent/path")
        assert len(router.routes) == 0

    def test_root_route(self) -> None:
        """Router should match root route."""
        router = Router(ROUTES_DIR)
        handler, params = router.match("/", "GET")
        assert handler is not None
        assert params == {}


class TestTrieRouting:
    """Test Trie-specific routing behavior."""

    def test_static_priority_over_dynamic(self) -> None:
        """Static routes should be prioritized over dynamic routes."""
        from pykour.router import TrieNode

        router = Router(ROUTES_DIR)
        # Clear and manually set up routes for testing
        router._root = TrieNode()
        router._routes_cache = None

        # Register /api/users/[id] (dynamic)
        async def dynamic_handler(request):
            return None

        router._insert("/api/users/[id]", {"GET": dynamic_handler})

        # Register /api/users/me (static)
        async def static_handler(request):
            return None

        router._insert("/api/users/me", {"GET": static_handler})

        # Static should be matched
        handler, params = router.match("/api/users/me", "GET")
        assert handler is static_handler
        assert params == {}

        # Dynamic should still work for other paths
        handler, params = router.match("/api/users/123", "GET")
        assert handler is dynamic_handler
        assert params == {"id": "123"}

    def test_backtracking_when_static_fails(self) -> None:
        """Router should backtrack to dynamic when static path has no handler."""
        from pykour.router import TrieNode

        router = Router(ROUTES_DIR)
        router._root = TrieNode()
        router._routes_cache = None

        # Register /api/[category]/items
        async def category_handler(request):
            return None

        router._insert("/api/[category]/items", {"GET": category_handler})

        # Match should use dynamic segment
        handler, params = router.match("/api/electronics/items", "GET")
        assert handler is category_handler
        assert params == {"category": "electronics"}

    def test_catch_all_last_priority(self) -> None:
        """Catch-all should have lowest priority."""
        from pykour.router import TrieNode

        router = Router(ROUTES_DIR)
        router._root = TrieNode()
        router._routes_cache = None

        # Register catch-all
        async def catch_all_handler(request):
            return None

        router._insert("/docs/[...slug]", {"GET": catch_all_handler})

        # Register specific static route
        async def specific_handler(request):
            return None

        router._insert("/docs/intro", {"GET": specific_handler})

        # Static should be matched
        handler, params = router.match("/docs/intro", "GET")
        assert handler is specific_handler
        assert params == {}

        # Catch-all should handle other paths
        handler, params = router.match("/docs/guide/getting-started", "GET")
        assert handler is catch_all_handler
        assert params == {"slug": "guide/getting-started"}

    def test_param_extraction_accuracy(self) -> None:
        """Parameters should be extracted accurately."""
        from pykour.router import TrieNode

        router = Router(ROUTES_DIR)
        router._root = TrieNode()
        router._routes_cache = None

        async def handler(request):
            return None

        router._insert(
            "/users/[userId]/posts/[postId]/comments/[commentId]", {"GET": handler}
        )

        handler_result, params = router.match(
            "/users/abc/posts/123/comments/xyz", "GET"
        )
        assert handler_result is handler
        assert params == {"userId": "abc", "postId": "123", "commentId": "xyz"}

    def test_multiple_dynamic_segments(self) -> None:
        """Multiple dynamic segments should all be captured."""
        from pykour.router import TrieNode

        router = Router(ROUTES_DIR)
        router._root = TrieNode()
        router._routes_cache = None

        async def handler(request):
            return None

        router._insert("/[org]/[repo]/tree/[branch]", {"GET": handler})

        handler_result, params = router.match("/anthropic/claude/tree/main", "GET")
        assert handler_result is handler
        assert params == {"org": "anthropic", "repo": "claude", "branch": "main"}

    def test_path_normalization_trailing_slash(self) -> None:
        """Trailing slashes should be normalized."""
        from pykour.router import TrieNode

        router = Router(ROUTES_DIR)
        router._root = TrieNode()
        router._routes_cache = None

        async def handler(request):
            return None

        router._insert("/api/users", {"GET": handler})

        # Both with and without trailing slash should match
        handler1, _ = router.match("/api/users", "GET")
        handler2, _ = router.match("/api/users/", "GET")
        assert handler1 is handler
        assert handler2 is handler

    def test_path_normalization_multiple_slashes(self) -> None:
        """Multiple consecutive slashes should be collapsed."""
        from pykour.router import TrieNode

        router = Router(ROUTES_DIR)
        router._root = TrieNode()
        router._routes_cache = None

        async def handler(request):
            return None

        router._insert("/api/users", {"GET": handler})

        # Multiple slashes should still match
        handler_result, _ = router.match("/api//users", "GET")
        assert handler_result is handler

    def test_routes_property_backward_compatibility(self) -> None:
        """routes property should return list of Route objects."""
        router = Router(ROUTES_DIR)

        # routes should be a list
        assert isinstance(router.routes, list)

        # Each route should have expected attributes
        for route in router.routes:
            assert hasattr(route, "path_pattern")
            assert hasattr(route, "handlers")
            assert hasattr(route, "param_names")
            assert hasattr(route, "match")

    def test_head_method_implicit(self) -> None:
        """HEAD should be allowed when GET is defined."""
        router = Router(ROUTES_DIR)

        # Get methods for a GET route
        methods = router.get_allowed_methods("/api/users")

        # HEAD should be implicitly allowed
        assert "HEAD" in methods
        assert "GET" in methods
