"""Tests for cache client."""

import pytest

from pykour.cache.client import Cache
from pykour.cache.serializers import JSONSerializer
from pykour.cache.storage import InMemoryStorage


class TestCache:
    """Tests for Cache client."""

    @pytest.fixture
    def storage(self) -> InMemoryStorage:
        """Create a fresh InMemoryStorage instance."""
        return InMemoryStorage()

    @pytest.fixture
    def cache(self, storage: InMemoryStorage) -> Cache:
        """Create a Cache instance with InMemoryStorage."""
        return Cache(storage)

    async def test_get_set_basic(self, cache: Cache) -> None:
        """Test basic get/set operations."""
        await cache.set("key1", {"name": "Alice", "age": 30})
        result = await cache.get("key1")
        assert result == {"name": "Alice", "age": 30}

    async def test_get_nonexistent_key(self, cache: Cache) -> None:
        """Test getting a nonexistent key returns None."""
        result = await cache.get("nonexistent")
        assert result is None

    async def test_set_with_ttl(self, cache: Cache) -> None:
        """Test setting value with TTL."""
        await cache.set("key1", "value1", ttl=300)
        result = await cache.get("key1")
        assert result == "value1"

    async def test_delete(self, cache: Cache) -> None:
        """Test deleting a key."""
        await cache.set("key1", "value1")
        result = await cache.delete("key1")
        assert result is True
        assert await cache.get("key1") is None

    async def test_delete_nonexistent(self, cache: Cache) -> None:
        """Test deleting a nonexistent key."""
        result = await cache.delete("nonexistent")
        assert result is False

    async def test_delete_pattern(self, cache: Cache) -> None:
        """Test deleting keys by pattern."""
        await cache.set("user:1", {"id": 1})
        await cache.set("user:2", {"id": 2})
        await cache.set("other:1", {"id": 1})

        deleted = await cache.delete_pattern("user:*")
        assert deleted == 2

        assert await cache.get("user:1") is None
        assert await cache.get("other:1") == {"id": 1}

    async def test_exists(self, cache: Cache) -> None:
        """Test exists check."""
        await cache.set("key1", "value1")
        assert await cache.exists("key1") is True
        assert await cache.exists("nonexistent") is False

    async def test_clear(self, cache: Cache) -> None:
        """Test clearing all entries."""
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.clear()
        assert await cache.get("key1") is None
        assert await cache.get("key2") is None

    async def test_get_or_set_miss(self, cache: Cache) -> None:
        """Test get_or_set on cache miss."""
        call_count = 0

        def factory() -> dict:
            nonlocal call_count
            call_count += 1
            return {"computed": True}

        result = await cache.get_or_set("key1", factory, ttl=300)
        assert result == {"computed": True}
        assert call_count == 1

        # Second call should use cached value
        result = await cache.get_or_set("key1", factory, ttl=300)
        assert result == {"computed": True}
        assert call_count == 1  # Factory not called again

    async def test_get_or_set_with_async_factory(self, cache: Cache) -> None:
        """Test get_or_set with async factory."""
        call_count = 0

        async def async_factory() -> dict:
            nonlocal call_count
            call_count += 1
            return {"async_computed": True}

        result = await cache.get_or_set("key1", async_factory, ttl=300)
        assert result == {"async_computed": True}
        assert call_count == 1

    async def test_complex_data_types(self, cache: Cache) -> None:
        """Test caching complex data types."""
        # List
        await cache.set("list", [1, 2, 3, {"nested": True}])
        assert await cache.get("list") == [1, 2, 3, {"nested": True}]

        # Nested dict
        await cache.set("nested", {"a": {"b": {"c": [1, 2, 3]}}})
        assert await cache.get("nested") == {"a": {"b": {"c": [1, 2, 3]}}}

        # Unicode strings
        await cache.set("unicode", {"msg": "こんにちは世界"})
        assert await cache.get("unicode") == {"msg": "こんにちは世界"}

    async def test_storage_property(
        self, cache: Cache, storage: InMemoryStorage
    ) -> None:
        """Test storage property returns the underlying storage."""
        assert cache.storage is storage

    async def test_custom_serializer(self, storage: InMemoryStorage) -> None:
        """Test Cache with custom serializer."""
        serializer = JSONSerializer(ensure_ascii=True)
        cache = Cache(storage, serializer=serializer)

        await cache.set("key1", {"name": "テスト"})
        result = await cache.get("key1")
        assert result == {"name": "テスト"}
