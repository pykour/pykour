"""Cache client for programmatic cache access."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable
from typing import Any, Callable, TypeVar, cast

from pykour.cache.serializers import JSONSerializer, Serializer
from pykour.cache.storage import CacheStorage

T = TypeVar("T")


class Cache:
    """Programmatic cache access for arbitrary data caching.

    Provides a high-level API for caching arbitrary data with
    automatic serialization/deserialization.

    Example:
        from pykour.cache import Cache
        from pykour.di import Depends

        async def handler(cache: Cache = Depends()) -> JSONResponse:
            # Get cached value
            user = await cache.get("user:123")

            # Set with TTL
            await cache.set("user:123", user_data, ttl=300)

            # Delete
            await cache.delete("user:123")

            # Check existence
            if await cache.exists("user:123"):
                ...

            # Get or compute
            data = await cache.get_or_set(
                "expensive:data",
                factory=compute_expensive_data,
                ttl=3600,
            )
    """

    def __init__(
        self,
        storage: CacheStorage,
        serializer: Serializer | None = None,
    ) -> None:
        """Initialize cache client.

        Args:
            storage: Cache storage backend.
            serializer: Value serializer. Defaults to JSONSerializer.
        """
        self._storage = storage
        self._serializer = serializer or JSONSerializer()

    @property
    def storage(self) -> CacheStorage:
        """Get the underlying storage backend."""
        return self._storage

    async def get(self, key: str) -> Any | None:
        """Get cached value.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """
        data = await self._storage.get(key)
        if data is None:
            return None
        return self._serializer.deserialize(data)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """Set cached value.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds. None means no expiration.
        """
        data = self._serializer.serialize(value)
        await self._storage.set(key, data, ttl)

    async def delete(self, key: str) -> bool:
        """Delete cached value.

        Args:
            key: Cache key.

        Returns:
            True if key existed and was deleted.
        """
        return await self._storage.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "user:*").

        Returns:
            Number of keys deleted.
        """
        return await self._storage.delete_pattern(pattern)

    async def exists(self, key: str) -> bool:
        """Check if key exists.

        Args:
            key: Cache key.

        Returns:
            True if key exists and is not expired.
        """
        return await self._storage.exists(key)

    async def clear(self) -> None:
        """Clear all cached entries."""
        await self._storage.clear()

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], T | Awaitable[T]],
        ttl: int | None = None,
    ) -> T:
        """Get cached value or compute and cache it.

        Useful for caching expensive computations or database queries.

        Args:
            key: Cache key.
            factory: Callable that returns the value to cache.
                     Can be sync or async.
            ttl: Time-to-live in seconds for newly cached values.

        Returns:
            Cached or newly computed value.

        Example:
            # Cache database query results
            users = await cache.get_or_set(
                "users:active",
                factory=lambda: db.select("*").from_("users").where(active=True).fetch_all(),
                ttl=300,
            )

            # Cache with async factory
            async def fetch_user_details():
                user = await db.select("*").from_("users").where(id=1).fetch_one()
                profile = await db.select("*").from_("profiles").where(user_id=1).fetch_one()
                return {"user": user, "profile": profile}

            data = await cache.get_or_set("user:1:details", fetch_user_details, ttl=600)
        """
        cached = await self.get(key)
        if cached is not None:
            return cast(T, cached)

        result = factory()
        # Handle both sync and async factories
        if inspect.isawaitable(result):
            computed = cast(T, await result)
        else:
            computed = cast(T, result)

        await self.set(key, computed, ttl)
        return computed
