"""Cache decorators for declarative caching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

# Registry attribute names for cache metadata
CACHE_REGISTRY_ATTR = "__pykour_cache__"
CACHE_EVICT_REGISTRY_ATTR = "__pykour_cache_evict__"

F = TypeVar("F", bound=Callable[..., object])


@dataclass
class CacheInfo:
    """Cache decorator metadata.

    Attributes:
        key: Cache key template with {param} placeholders.
        ttl: Time-to-live in seconds. None means no expiration.
    """

    key: str
    ttl: int | None = None


@dataclass
class CacheEvictInfo:
    """Cache eviction decorator metadata.

    Attributes:
        key: Key or pattern to evict. Use {param} for interpolation.
        all_entries: If True, treat key as glob pattern and evict all matches.
    """

    key: str
    all_entries: bool = False


def cache(
    key: str,
    ttl: int | None = None,
) -> Callable[[F], F]:
    """Decorator to cache handler responses.

    Cache responses based on a key template. The key can include
    parameter placeholders that are interpolated at runtime.

    Args:
        key: Cache key template. Use {param} for parameter interpolation.
             Example: "user:{id}" uses the 'id' parameter value.
        ttl: Time-to-live in seconds. None means no expiration.

    Returns:
        Decorator function.

    Example:
        @cache(key="user:{id}", ttl=300)
        async def get(request: Request, id: int = Path()) -> JSONResponse:
            user = await db.select("*").from_("users").where(id=id).fetch_one()
            return JSONResponse({"user": user})

        @cache(key="users:list")
        async def list_users(request: Request) -> JSONResponse:
            users = await db.select("*").from_("users").fetch_all()
            return JSONResponse({"users": users})
    """

    def decorator(func: F) -> F:
        if not hasattr(func, CACHE_REGISTRY_ATTR):
            setattr(func, CACHE_REGISTRY_ATTR, [])

        getattr(func, CACHE_REGISTRY_ATTR).append(CacheInfo(key=key, ttl=ttl))
        return func

    return decorator


def cache_evict(
    key: str,
    all_entries: bool = False,
) -> Callable[[F], F]:
    """Decorator to evict cache entries after handler execution.

    Evict cached entries when data is modified. Can evict a single
    key or multiple keys matching a pattern.

    Args:
        key: Key or pattern to evict. Use {param} for parameter interpolation.
             Use '*' for pattern matching (e.g., "user:*").
        all_entries: If True, treat key as glob pattern and evict all matches.
                     Required when using wildcard patterns.

    Returns:
        Decorator function.

    Example:
        @cache_evict(key="user:{id}")
        async def put(request: Request, id: int = Path()) -> JSONResponse:
            await db.update("users").set(name="new").where(id=id).execute()
            return JSONResponse({"updated": True})

        @cache_evict(key="users:*", all_entries=True)
        async def delete_all(request: Request) -> JSONResponse:
            await db.delete("users").execute()
            return JSONResponse({"deleted": True})
    """

    def decorator(func: F) -> F:
        if not hasattr(func, CACHE_EVICT_REGISTRY_ATTR):
            setattr(func, CACHE_EVICT_REGISTRY_ATTR, [])

        getattr(func, CACHE_EVICT_REGISTRY_ATTR).append(
            CacheEvictInfo(key=key, all_entries=all_entries)
        )
        return func

    return decorator


def get_cache_info(func: Callable[..., object]) -> list[CacheInfo]:
    """Get cache metadata from a function.

    Args:
        func: Function to inspect.

    Returns:
        List of CacheInfo metadata, or empty list if not cached.
    """
    return getattr(func, CACHE_REGISTRY_ATTR, [])


def get_cache_evict_info(func: Callable[..., object]) -> list[CacheEvictInfo]:
    """Get cache eviction metadata from a function.

    Args:
        func: Function to inspect.

    Returns:
        List of CacheEvictInfo metadata, or empty list if no evictions.
    """
    return getattr(func, CACHE_EVICT_REGISTRY_ATTR, [])
