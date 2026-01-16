"""Integration tests for cache with Pykour application."""

import pytest

from pykour import JSONResponse, Pykour, Request
from pykour.cache import Cache, InMemoryStorage, cache, cache_evict
from pykour.cache.decorators import get_cache_info
from pykour.di import Depends
from pykour.testing import TestClient


class TestCacheIntegration:
    """Integration tests for cache with Pykour application."""

    @pytest.fixture
    def storage(self) -> InMemoryStorage:
        """Create a fresh InMemoryStorage instance."""
        return InMemoryStorage()

    async def test_cache_decorator_caches_response(
        self, storage: InMemoryStorage
    ) -> None:
        """Test that @cache decorator caches handler responses."""
        call_count = 0

        @cache(key="user:{id}", ttl=300)
        async def get_user(request: Request, id: int) -> JSONResponse:
            nonlocal call_count
            call_count += 1
            return JSONResponse({"id": id, "name": f"User {id}"})

        # Create app with custom routing
        app = Pykour(routes_dir="tests/routes", cache=storage)
        # Manually register the handler for testing
        from pykour.router import TrieNode

        app._router._root = TrieNode()
        app._router._routes_cache = None
        app._router._insert("/users/[id]", {"GET": get_user})

        client = TestClient(app)

        # First request - should call handler
        response1 = await client.get("/users/123")
        assert response1.status_code == 200
        assert response1.json() == {"id": 123, "name": "User 123"}
        assert call_count == 1

        # Second request - should return cached response
        response2 = await client.get("/users/123")
        assert response2.status_code == 200
        assert response2.json() == {"id": 123, "name": "User 123"}
        assert call_count == 1  # Handler not called again

        # Different ID - should call handler
        response3 = await client.get("/users/456")
        assert response3.status_code == 200
        assert response3.json() == {"id": 456, "name": "User 456"}
        assert call_count == 2

    async def test_cache_evict_decorator_invalidates_cache(
        self, storage: InMemoryStorage
    ) -> None:
        """Test that @cache_evict decorator invalidates cache."""
        # Pre-populate cache
        cache_client = Cache(storage)
        await cache_client.set("user:123", {"id": 123, "cached": True})

        @cache_evict(key="user:{id}")
        async def update_user(request: Request, id: int) -> JSONResponse:
            return JSONResponse({"id": id, "updated": True})

        app = Pykour(routes_dir="tests/routes", cache=storage)
        from pykour.router import TrieNode

        app._router._root = TrieNode()
        app._router._routes_cache = None
        app._router._insert("/users/[id]", {"PUT": update_user})

        client = TestClient(app)

        # Verify cache entry exists
        assert await storage.exists("user:123") is True

        # Call handler with evict decorator
        response = await client.put("/users/123", json={"name": "Updated"})
        assert response.status_code == 200

        # Cache should be invalidated
        assert await storage.exists("user:123") is False

    async def test_cache_evict_with_pattern(self, storage: InMemoryStorage) -> None:
        """Test @cache_evict with pattern matching."""
        # Pre-populate cache
        await storage.set("user:1", b"data1")
        await storage.set("user:2", b"data2")
        await storage.set("other:1", b"other")

        @cache_evict(key="user:*", all_entries=True)
        async def delete_all_users(request: Request) -> JSONResponse:
            return JSONResponse({"deleted": True})

        app = Pykour(routes_dir="tests/routes", cache=storage)
        from pykour.router import TrieNode

        app._router._root = TrieNode()
        app._router._routes_cache = None
        app._router._insert("/users", {"DELETE": delete_all_users})

        client = TestClient(app)
        response = await client.delete("/users")
        assert response.status_code == 204  # DELETE returns 204 by default

        # User entries should be deleted
        assert await storage.exists("user:1") is False
        assert await storage.exists("user:2") is False
        # Other entries should remain
        assert await storage.exists("other:1") is True

    async def test_cache_client_via_di(self, storage: InMemoryStorage) -> None:
        """Test Cache client injection via DI."""

        async def handler_with_cache(
            request: Request,
            cache: Cache = Depends(),  # type: ignore[assignment]
        ) -> JSONResponse:
            # Use cache programmatically
            data = await cache.get("my_key")
            if data is None:
                data = {"computed": True}
                await cache.set("my_key", data, ttl=300)
            return JSONResponse(data)

        app = Pykour(routes_dir="tests/routes", cache=storage)
        from pykour.router import TrieNode

        app._router._root = TrieNode()
        app._router._routes_cache = None
        app._router._insert("/", {"GET": handler_with_cache})

        client = TestClient(app)

        # First request - computes and caches
        response1 = await client.get("/")
        assert response1.status_code == 200
        assert response1.json() == {"computed": True}

        # Verify data was cached via client
        cache_client = Cache(storage)
        cached = await cache_client.get("my_key")
        assert cached == {"computed": True}

    async def test_cache_not_applied_without_storage(self) -> None:
        """Test that cache decorators are no-op when no storage is configured."""
        call_count = 0

        @cache(key="test", ttl=300)
        async def cached_handler(request: Request) -> JSONResponse:
            nonlocal call_count
            call_count += 1
            return JSONResponse({"count": call_count})

        # App without cache
        app = Pykour(routes_dir="tests/routes")
        from pykour.router import TrieNode

        app._router._root = TrieNode()
        app._router._routes_cache = None
        app._router._insert("/", {"GET": cached_handler})

        client = TestClient(app)

        # Each request should call handler (no caching)
        response1 = await client.get("/")
        assert response1.json() == {"count": 1}

        response2 = await client.get("/")
        assert response2.json() == {"count": 2}

    async def test_only_2xx_responses_are_cached(
        self, storage: InMemoryStorage
    ) -> None:
        """Test that only successful (2xx) responses are cached."""
        call_count = 0

        @cache(key="error", ttl=300)
        async def error_handler(request: Request) -> JSONResponse:
            nonlocal call_count
            call_count += 1
            return JSONResponse({"error": "Not found"}, status_code=404)

        app = Pykour(routes_dir="tests/routes", cache=storage)
        from pykour.router import TrieNode

        app._router._root = TrieNode()
        app._router._routes_cache = None
        app._router._insert("/error", {"GET": error_handler})

        client = TestClient(app)

        # First request
        response1 = await client.get("/error")
        assert response1.status_code == 404
        assert call_count == 1

        # Second request - should NOT use cache (404 not cached)
        response2 = await client.get("/error")
        assert response2.status_code == 404
        assert call_count == 2  # Handler called again


class TestCacheKeyInterpolation:
    """Tests for cache key interpolation."""

    def test_get_cache_info_from_decorated_function(self) -> None:
        """Test that cache info can be retrieved from decorated function."""

        @cache(key="user:{id}:{action}", ttl=300)
        async def handler(id: int, action: str) -> JSONResponse:
            return JSONResponse({})

        infos = get_cache_info(handler)
        assert len(infos) == 1
        assert infos[0].key == "user:{id}:{action}"
        assert infos[0].ttl == 300
