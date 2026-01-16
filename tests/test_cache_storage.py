"""Tests for cache storage backends."""

import asyncio
import time

import pytest

from pykour.cache.storage import CacheEntry, CacheStorage, InMemoryStorage


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_entry_not_expired_without_ttl(self) -> None:
        """Entry without TTL should never expire."""
        entry = CacheEntry(value=b"test", ttl=None)
        assert not entry.is_expired()

    def test_entry_not_expired_within_ttl(self) -> None:
        """Entry within TTL should not be expired."""
        entry = CacheEntry(value=b"test", ttl=10)
        assert not entry.is_expired()

    def test_entry_expired_after_ttl(self) -> None:
        """Entry after TTL should be expired."""
        entry = CacheEntry(value=b"test", created_at=time.time() - 10, ttl=5)
        assert entry.is_expired()


class TestInMemoryStorage:
    """Tests for InMemoryStorage."""

    @pytest.fixture
    def storage(self) -> InMemoryStorage:
        """Create a fresh InMemoryStorage instance."""
        return InMemoryStorage()

    async def test_get_set_basic(self, storage: InMemoryStorage) -> None:
        """Test basic get/set operations."""
        await storage.set("key1", b"value1")
        result = await storage.get("key1")
        assert result == b"value1"

    async def test_get_nonexistent_key(self, storage: InMemoryStorage) -> None:
        """Test getting a nonexistent key returns None."""
        result = await storage.get("nonexistent")
        assert result is None

    async def test_set_with_ttl(self, storage: InMemoryStorage) -> None:
        """Test setting value with TTL."""
        await storage.set("key1", b"value1", ttl=10)
        result = await storage.get("key1")
        assert result == b"value1"

    async def test_get_expired_key(self, storage: InMemoryStorage) -> None:
        """Test that expired keys return None."""
        # Set with very short TTL
        await storage.set("key1", b"value1", ttl=0)
        # Wait for expiration
        await asyncio.sleep(0.01)
        result = await storage.get("key1")
        assert result is None

    async def test_delete_existing_key(self, storage: InMemoryStorage) -> None:
        """Test deleting an existing key."""
        await storage.set("key1", b"value1")
        result = await storage.delete("key1")
        assert result is True
        assert await storage.get("key1") is None

    async def test_delete_nonexistent_key(self, storage: InMemoryStorage) -> None:
        """Test deleting a nonexistent key returns False."""
        result = await storage.delete("nonexistent")
        assert result is False

    async def test_delete_pattern(self, storage: InMemoryStorage) -> None:
        """Test deleting keys by pattern."""
        await storage.set("user:1", b"value1")
        await storage.set("user:2", b"value2")
        await storage.set("user:3", b"value3")
        await storage.set("other:1", b"other")

        deleted = await storage.delete_pattern("user:*")
        assert deleted == 3

        assert await storage.get("user:1") is None
        assert await storage.get("user:2") is None
        assert await storage.get("user:3") is None
        assert await storage.get("other:1") == b"other"

    async def test_exists(self, storage: InMemoryStorage) -> None:
        """Test exists check."""
        await storage.set("key1", b"value1")
        assert await storage.exists("key1") is True
        assert await storage.exists("nonexistent") is False

    async def test_exists_expired_key(self, storage: InMemoryStorage) -> None:
        """Test that exists returns False for expired keys."""
        await storage.set("key1", b"value1", ttl=0)
        await asyncio.sleep(0.01)
        assert await storage.exists("key1") is False

    async def test_clear(self, storage: InMemoryStorage) -> None:
        """Test clearing all entries."""
        await storage.set("key1", b"value1")
        await storage.set("key2", b"value2")
        await storage.clear()
        assert await storage.get("key1") is None
        assert await storage.get("key2") is None

    async def test_overwrite_existing_key(self, storage: InMemoryStorage) -> None:
        """Test overwriting an existing key."""
        await storage.set("key1", b"value1")
        await storage.set("key1", b"value2")
        result = await storage.get("key1")
        assert result == b"value2"

    async def test_connect_disconnect_are_noop(self, storage: InMemoryStorage) -> None:
        """Test that connect/disconnect don't raise errors."""
        await storage.connect()
        await storage.disconnect()
        # Should still work after disconnect for in-memory
        await storage.set("key1", b"value1")
        assert await storage.get("key1") == b"value1"


class TestCacheStorageABC:
    """Tests for CacheStorage ABC."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Test that CacheStorage cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CacheStorage()
