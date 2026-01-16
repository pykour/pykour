"""Valkey (Redis-compatible) cache storage backend."""

from __future__ import annotations

from typing import Any

from pykour.cache.exceptions import CacheConnectionError
from pykour.cache.storage import CacheStorage

try:
    import valkey.asyncio as valkey  # type: ignore[import-untyped]
except ImportError as e:
    raise ImportError(
        "valkey-py is required for ValkeyStorage. Install it with: pip install valkey"
    ) from e


class ValkeyStorage(CacheStorage):
    """Valkey (Redis-compatible) cache storage backend.

    Uses the valkey-py library for async Redis/Valkey operations.
    Suitable for production deployments with distributed caching.

    Example:
        from pykour import Pykour
        from pykour.cache import ValkeyStorage

        app = Pykour(
            routes_dir="routes",
            cache=ValkeyStorage("valkey://localhost:6379"),
        )

        # With authentication and SSL
        app = Pykour(
            routes_dir="routes",
            cache=ValkeyStorage(
                "valkeys://user:password@localhost:6379/0",
                prefix="myapp:",
            ),
        )
    """

    def __init__(
        self,
        url: str = "valkey://localhost:6379",
        prefix: str = "pykour:",
        **options: Any,
    ) -> None:
        """Initialize Valkey storage.

        Args:
            url: Valkey connection URL. Supports:
                - valkey://localhost:6379 (standard)
                - valkeys://localhost:6379 (SSL)
                - valkey://user:pass@localhost:6379/0 (auth + db)
            prefix: Key prefix for all cache keys. Default "pykour:".
            **options: Additional options passed to valkey.from_url().
        """
        self._url = url
        self._prefix = prefix
        self._options = options
        self._client: valkey.Valkey | None = None

    def _make_key(self, key: str) -> str:
        """Add prefix to cache key."""
        return f"{self._prefix}{key}"

    async def connect(self) -> None:
        """Establish connection to Valkey."""
        if self._client is not None:
            return

        try:
            self._client = valkey.from_url(self._url, **self._options)
            # Test connection
            await self._client.ping()
        except Exception as e:
            self._client = None
            raise CacheConnectionError(f"Failed to connect to Valkey: {e}") from e

    async def disconnect(self) -> None:
        """Close connection to Valkey."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _ensure_connected(self) -> valkey.Valkey:
        """Ensure client is connected and return it."""
        if self._client is None:
            raise CacheConnectionError(
                "Valkey client not connected. Call connect() first."
            )
        return self._client

    async def get(self, key: str) -> bytes | None:
        """Get value by key."""
        client = self._ensure_connected()
        result = await client.get(self._make_key(key))
        return result

    async def set(self, key: str, value: bytes, ttl: int | None = None) -> None:
        """Set value with optional TTL."""
        client = self._ensure_connected()
        full_key = self._make_key(key)
        if ttl is not None:
            await client.setex(full_key, ttl, value)
        else:
            await client.set(full_key, value)

    async def delete(self, key: str) -> bool:
        """Delete a key."""
        client = self._ensure_connected()
        result = await client.delete(self._make_key(key))
        return result > 0

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern.

        Note: Uses SCAN for safe iteration in production environments.
        """
        client = self._ensure_connected()
        full_pattern = self._make_key(pattern)

        deleted = 0
        cursor = 0
        while True:
            cursor, keys = await client.scan(cursor, match=full_pattern, count=100)
            if keys:
                deleted += await client.delete(*keys)
            if cursor == 0:
                break

        return deleted

    async def exists(self, key: str) -> bool:
        """Check if a key exists."""
        client = self._ensure_connected()
        result = await client.exists(self._make_key(key))
        return result > 0

    async def clear(self) -> None:
        """Clear all cached entries with the configured prefix.

        Note: Only deletes keys with the configured prefix, not all keys.
        """
        await self.delete_pattern("*")
