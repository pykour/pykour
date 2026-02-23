---
title: Caching
parent: Advanced
nav_order: 1
---

# Caching
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

Pykour provides a built-in caching system with decorator-based response caching and a programmatic `Cache` client. Two storage backends are included: in-memory (for development and single-instance deployments) and Valkey/Redis (for production distributed caching).

## Setup

Pass a `CacheStorage` instance to the `Pykour` constructor:

```python
from pykour import Pykour
from pykour.cache import InMemoryStorage

app = Pykour(
    routes_dir="routes",
    cache=InMemoryStorage(),
)
```

For Valkey (Redis-compatible) in production:

```python
from pykour import Pykour
from pykour.cache import ValkeyStorage

app = Pykour(
    routes_dir="routes",
    cache=ValkeyStorage("valkey://localhost:6379"),
)
```

You can also configure cache via `pykour.toml`:

```toml
[cache]
url = "valkey://localhost:6379"
prefix = "myapp:"
```

## The `@cache` Decorator

The `@cache` decorator caches handler responses based on a key template. The key can include `{param}` placeholders that are interpolated from handler parameters at runtime.

```python
from pykour.cache import cache
from pykour import Request, JSONResponse
from pykour.params import Path

@cache(key="user:{id}", ttl=300)
async def get(request: Request, id: int = Path()) -> JSONResponse:
    user = await db.select("*").from_("users").where(id=id).fetch_one()
    return JSONResponse({"user": user})
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Cache key template. Use `{param}` for parameter interpolation. |
| `ttl` | `int \| None` | Time-to-live in seconds. `None` means no expiration. |

### Static Keys

For responses that don't vary by parameter:

```python
@cache(key="users:list")
async def get(request: Request) -> JSONResponse:
    users = await db.select("*").from_("users").fetch_all()
    return JSONResponse({"users": users})
```

## The `@cache_evict` Decorator

The `@cache_evict` decorator removes cached entries when data is modified. This keeps your cache consistent with the underlying data.

```python
from pykour.cache import cache_evict

@cache_evict(key="user:{id}")
async def put(request: Request, id: int = Path()) -> JSONResponse:
    await db.update("users").set(name="new").where(id=id).execute()
    return JSONResponse({"updated": True})
```

### Evicting Multiple Keys

Use glob patterns with `all_entries=True` to evict groups of keys:

```python
@cache_evict(key="users:*", all_entries=True)
async def delete(request: Request) -> JSONResponse:
    await db.delete("users").execute()
    return JSONResponse({"deleted": True})
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | -- | Key or pattern to evict. Use `{param}` for interpolation. |
| `all_entries` | `bool` | `False` | If `True`, treat key as glob pattern and evict all matches. |

## Programmatic Cache Client

The `Cache` class provides a high-level API for caching arbitrary data. It can be injected into handlers via dependency injection.

```python
from pykour.cache import Cache
from pykour.di import Depends

async def get(request: Request, cache: Cache = Depends()) -> JSONResponse:
    # Get cached value
    user = await cache.get("user:123")

    # Set with TTL
    await cache.set("user:123", user_data, ttl=300)

    # Delete
    await cache.delete("user:123")

    # Check existence
    if await cache.exists("user:123"):
        ...

    return JSONResponse({"user": user})
```

### `get_or_set` Pattern

The `get_or_set` method retrieves a cached value or computes and caches it if not found. This is useful for caching expensive computations:

```python
async def get(request: Request, cache: Cache = Depends()) -> JSONResponse:
    users = await cache.get_or_set(
        "users:active",
        factory=lambda: db.select("*").from_("users").where(active=True).fetch_all(),
        ttl=300,
    )
    return JSONResponse({"users": users})
```

The factory can be sync or async:

```python
async def fetch_user_details():
    user = await db.select("*").from_("users").where(id=1).fetch_one()
    profile = await db.select("*").from_("profiles").where(user_id=1).fetch_one()
    return {"user": user, "profile": profile}

data = await cache.get_or_set("user:1:details", fetch_user_details, ttl=600)
```

### Cache API Reference

| Method | Signature | Description |
|--------|-----------|-------------|
| `get` | `async get(key: str) -> Any \| None` | Get cached value, or `None` if not found. |
| `set` | `async set(key: str, value: Any, ttl: int \| None = None) -> None` | Set a value with optional TTL. |
| `delete` | `async delete(key: str) -> bool` | Delete a key. Returns `True` if it existed. |
| `delete_pattern` | `async delete_pattern(pattern: str) -> int` | Delete all keys matching a glob pattern. Returns count. |
| `exists` | `async exists(key: str) -> bool` | Check if key exists and is not expired. |
| `clear` | `async clear() -> None` | Clear all cached entries. |
| `get_or_set` | `async get_or_set(key: str, factory: Callable, ttl: int \| None = None) -> T` | Get cached value or compute and cache it. |

## Storage Backends

### InMemoryStorage

Suitable for development, testing, and single-instance deployments. Uses a Python `dict` with `asyncio.Lock` for thread safety.

```python
from pykour.cache import InMemoryStorage

storage = InMemoryStorage(cleanup_interval=60.0)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cleanup_interval` | `float` | `60.0` | Minimum seconds between automatic cleanup of expired entries. |

### ValkeyStorage

Production-ready backend using Valkey (Redis-compatible) for distributed caching. Requires the `valkey` package.

```python
from pykour.cache import ValkeyStorage

storage = ValkeyStorage(
    url="valkey://localhost:6379",
    prefix="myapp:",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | `str` | `"valkey://localhost:6379"` | Connection URL. Supports `valkey://`, `valkeys://` (SSL), and auth. |
| `prefix` | `str` | `"pykour:"` | Key prefix for all cache keys. |
| `**options` | `Any` | -- | Additional options passed to `valkey.from_url()`. |

#### URL Formats

```
valkey://localhost:6379          # Standard
valkeys://localhost:6379         # SSL
valkey://user:pass@host:6379/0   # Auth + database
```

### Custom Storage Backend

Implement the `CacheStorage` abstract base class:

```python
from pykour.cache.storage import CacheStorage

class MyStorage(CacheStorage):
    async def get(self, key: str) -> bytes | None: ...
    async def set(self, key: str, value: bytes, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> bool: ...
    async def delete_pattern(self, pattern: str) -> int: ...
    async def exists(self, key: str) -> bool: ...
    async def clear(self) -> None: ...

    # Optional: override for remote backends
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
```

## Serializers

The `Cache` client uses serializers to convert Python objects to bytes for storage. Two built-in serializers are available:

- **`JSONSerializer`** (default) -- Safe, human-readable, cross-language compatible.
- **`PickleSerializer`** -- Supports arbitrary Python objects but is Python-specific.

```python
from pykour.cache.client import Cache
from pykour.cache.serializers import PickleSerializer

cache = Cache(storage, serializer=PickleSerializer())
```

---

{: .fs-2 .text-muted }
Pykour Documentation
