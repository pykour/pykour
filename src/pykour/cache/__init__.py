"""Pykour caching module.

Provides declarative response caching and programmatic data caching
with support for multiple storage backends.

Example:
    Declarative response caching:

    ```python
    from pykour.cache import cache, cache_evict

    @cache(key="user:{id}", ttl=300)
    async def get(request: Request, id: int = Path()) -> JSONResponse:
        user = await db.select("*").from_("users").where(id=id).fetch_one()
        return JSONResponse({"user": user})

    @cache_evict(key="user:{id}")
    async def put(request: Request, id: int = Path()) -> JSONResponse:
        await db.update("users").set(name="new").where(id=id).execute()
        return JSONResponse({"updated": True})
    ```

    Programmatic data caching:

    ```python
    from pykour.cache import Cache
    from pykour.di import Depends

    async def handler(cache: Cache = Depends()) -> JSONResponse:
        # Get or compute cached value
        data = await cache.get_or_set(
            "expensive:data",
            factory=compute_data,
            ttl=3600,
        )
        return JSONResponse({"data": data})
    ```

    Application setup:

    ```python
    from pykour import Pykour
    from pykour.cache import InMemoryStorage, ValkeyStorage

    # Development/testing
    app = Pykour(routes_dir="routes", cache=InMemoryStorage())

    # Production
    app = Pykour(routes_dir="routes", cache=ValkeyStorage("valkey://localhost:6379"))
    ```
"""

from pykour.cache.client import Cache
from pykour.cache.decorators import (
    CACHE_EVICT_REGISTRY_ATTR,
    CACHE_REGISTRY_ATTR,
    CacheEvictInfo,
    CacheInfo,
    cache,
    cache_evict,
    get_cache_evict_info,
    get_cache_info,
)
from pykour.cache.exceptions import (
    # New exception names (preferred)
    CacheConnectionException,
    CacheException,
    CacheKeyException,
    CacheSerializationException,
    # Legacy aliases (backward compatibility)
    CacheConnectionError,
    CacheError,
    CacheKeyError,
    CacheSerializationError,
)
from pykour.cache.serializers import JSONSerializer, PickleSerializer, Serializer
from pykour.cache.storage import CacheEntry, CacheStorage, InMemoryStorage

__all__ = [
    # Decorators
    "cache",
    "cache_evict",
    "CacheInfo",
    "CacheEvictInfo",
    "get_cache_info",
    "get_cache_evict_info",
    "CACHE_REGISTRY_ATTR",
    "CACHE_EVICT_REGISTRY_ATTR",
    # Storage
    "CacheStorage",
    "CacheEntry",
    "InMemoryStorage",
    # Client
    "Cache",
    # Serializers
    "Serializer",
    "JSONSerializer",
    "PickleSerializer",
    # Exceptions (new names)
    "CacheException",
    "CacheConnectionException",
    "CacheSerializationException",
    "CacheKeyException",
    # Exceptions (legacy aliases)
    "CacheError",
    "CacheConnectionError",
    "CacheSerializationError",
    "CacheKeyError",
]

# Optional Valkey import
try:
    from pykour.cache.valkey import ValkeyStorage  # noqa: F401

    __all__.append("ValkeyStorage")
except ImportError:
    pass
