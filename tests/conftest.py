"""Shared test fixtures and utilities for pykour tests."""

from __future__ import annotations

import pytest

from tests.helpers import (
    MockSend,
    create_noop_receive,
    create_noop_send,
    create_receive,
    create_scope,
)

# Re-export helpers for backwards compatibility
__all__ = [
    "create_scope",
    "create_receive",
    "create_noop_receive",
    "create_noop_send",
    "MockSend",
]


@pytest.fixture
def mock_send() -> MockSend:
    """Provide a fresh MockSend instance."""
    return MockSend()


# ---------------------------------------------------------------------------
# Cache fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cache_storage():
    """Create a fresh InMemoryStorage instance for caching.

    This is a function-scoped fixture that creates a new storage instance
    for each test, ensuring test isolation.
    """
    from pykour.cache.storage import InMemoryStorage

    return InMemoryStorage()


@pytest.fixture
def cache_client(cache_storage):
    """Create a Cache client instance with the cache_storage fixture.

    Depends on cache_storage fixture for the underlying storage.
    """
    from pykour.cache.client import Cache

    return Cache(cache_storage)
