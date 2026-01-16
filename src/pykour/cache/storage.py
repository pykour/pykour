"""Cache storage backends."""

from __future__ import annotations

import fnmatch
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from pykour.common.storage import BaseInMemoryStorage


@dataclass
class CacheEntry:
    """Cached value with metadata."""

    value: bytes
    created_at: float = field(default_factory=time.time)
    ttl: int | None = None

    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl


class CacheStorage(ABC):
    """Abstract base class for cache storage backends.

    All methods are async to support both local and remote backends.
    """

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """Get value by key.

        Args:
            key: Cache key.

        Returns:
            Cached bytes or None if not found/expired.
        """
        ...

    @abstractmethod
    async def set(self, key: str, value: bytes, ttl: int | None = None) -> None:
        """Set value with optional TTL.

        Args:
            key: Cache key.
            value: Value to cache as bytes.
            ttl: Time-to-live in seconds. None means no expiration.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a key.

        Args:
            key: Cache key.

        Returns:
            True if key existed and was deleted, False otherwise.
        """
        ...

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "user:*").

        Returns:
            Number of keys deleted.
        """
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired.

        Args:
            key: Cache key.

        Returns:
            True if key exists and is not expired.
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached entries."""
        ...

    async def connect(self) -> None:
        """Establish connection to the storage backend.

        Override for remote backends that require connection setup.
        """
        pass

    async def disconnect(self) -> None:
        """Close connection to the storage backend.

        Override for remote backends that require cleanup.
        """
        pass


class InMemoryStorage(BaseInMemoryStorage[CacheEntry], CacheStorage):
    """In-memory cache storage using dict with asyncio.Lock.

    Suitable for development, testing, and single-instance deployments.
    Inherits from BaseInMemoryStorage for common lock/cleanup functionality.

    Example:
        storage = InMemoryStorage()
        await storage.set("key", b"value", ttl=300)
        value = await storage.get("key")
    """

    def __init__(self, cleanup_interval: float = 60.0) -> None:
        """Initialize in-memory storage.

        Args:
            cleanup_interval: Minimum seconds between automatic cleanup of
                expired entries. Default 60 seconds.
        """
        super().__init__(cleanup_interval=cleanup_interval)

    def _cleanup_expired_entries(self) -> list[str]:
        """Identify expired cache entries for cleanup."""
        return [key for key, entry in self._data.items() if entry.is_expired()]

    async def get(self, key: str) -> bytes | None:
        """Get value by key."""
        async with self._lock:
            await self._maybe_cleanup()

            entry = self._data.get(key)
            if entry is None:
                return None

            if entry.is_expired():
                del self._data[key]
                return None

            return entry.value

    async def set(self, key: str, value: bytes, ttl: int | None = None) -> None:
        """Set value with optional TTL."""
        async with self._lock:
            self._data[key] = CacheEntry(value=value, ttl=ttl)

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a glob pattern."""
        async with self._lock:
            matching_keys = [
                key for key in self._data.keys() if fnmatch.fnmatch(key, pattern)
            ]
            for key in matching_keys:
                del self._data[key]
            return len(matching_keys)

    async def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        async with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return False

            if entry.is_expired():
                del self._data[key]
                return False

            return True

    async def clear(self) -> None:
        """Clear all cached entries."""
        async with self._lock:
            self._clear_data()
