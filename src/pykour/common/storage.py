"""Common storage base classes for Pykour."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

# Type variable for storage data type
T = TypeVar("T")


class BaseInMemoryStorage(ABC, Generic[T]):
    """Abstract base class for in-memory storage backends.

    Provides common functionality for:
    - Async lock management for thread-safety
    - Periodic cleanup of expired entries
    - Dictionary-based data storage

    Subclasses must implement `_cleanup_expired_entries()` to define
    their specific cleanup logic.

    Type parameter T represents the stored data type.

    Example:
        class MyStorage(BaseInMemoryStorage[MyEntry]):
            def _cleanup_expired_entries(self) -> list[str]:
                # Return keys to remove
                return [k for k, v in self._data.items() if v.is_expired()]
    """

    def __init__(self, cleanup_interval: float = 60.0) -> None:
        """Initialize base in-memory storage.

        Args:
            cleanup_interval: Minimum seconds between automatic cleanup of
                expired entries. Default 60 seconds.
        """
        self._data: dict[str, T] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = cleanup_interval
        self._last_cleanup: float = 0.0

    @property
    def data(self) -> dict[str, T]:
        """Get the internal data dictionary (read-only access for subclasses)."""
        return self._data

    @property
    def lock(self) -> asyncio.Lock:
        """Get the internal lock for subclass use."""
        return self._lock

    @abstractmethod
    def _cleanup_expired_entries(self) -> list[str]:
        """Identify keys to remove during cleanup.

        Subclasses implement this to define their expiration logic.

        Returns:
            List of keys that should be removed.
        """
        ...

    async def _maybe_cleanup(self) -> None:
        """Remove expired entries if cleanup interval has passed.

        Should be called within a lock context.
        """
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        expired_keys = self._cleanup_expired_entries()
        for key in expired_keys:
            if key in self._data:
                del self._data[key]

    def _clear_data(self) -> None:
        """Clear all data. Should be called within a lock context."""
        self._data.clear()

    def __len__(self) -> int:
        """Return the number of entries in storage."""
        return len(self._data)
