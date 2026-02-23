---
title: Rate Limiting
parent: Middleware
nav_order: 4
---

# Rate Limiting

`RateLimitMiddleware` enforces request rate limits using the token bucket algorithm. It supports per-path configuration, custom key extraction, and pluggable storage backends.

## Basic usage

```python
from pykour import Pykour
from pykour.middleware import RateLimitMiddleware

app = Pykour()

app.add_middleware(
    RateLimitMiddleware,
    requests_per_second=10.0,
    burst_size=20,
)
```

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `requests_per_second` | `float` | `10.0` | Default token refill rate. |
| `burst_size` | `int` | `20` | Maximum bucket capacity (burst allowance). |
| `storage` | `RateLimitStorage \| None` | `None` | Storage backend. Defaults to `InMemoryStorage`. |
| `key_extractor` | `KeyExtractor \| None` | `None` | Function to extract rate limit key from ASGI scope. |
| `path_configs` | `dict[str, RateLimitConfig] \| None` | `None` | Path-specific rate limit settings with prefix matching. |
| `exclude_paths` | `list[str] \| None` | `None` | Paths to exclude from rate limiting. |
| `include_headers` | `bool` | `True` | Include rate limit headers in responses. |

## Token bucket algorithm

Each client gets a bucket with `burst_size` tokens. Tokens are consumed on each request and refill at `requests_per_second` rate:

- **Bucket capacity** (`burst_size`): Maximum number of tokens. Allows short bursts of traffic.
- **Refill rate** (`requests_per_second`): Tokens added per second. Controls sustained throughput.

When the bucket is empty, requests receive a `429 Too Many Requests` response with a `Retry-After` header.

## Per-path configuration

Use `RateLimitConfig` to set different limits for specific paths. Paths are matched by prefix:

```python
from pykour.middleware import RateLimitMiddleware, RateLimitConfig

app.add_middleware(
    RateLimitMiddleware,
    requests_per_second=10.0,
    burst_size=20,
    path_configs={
        "/api/auth/": RateLimitConfig(requests_per_second=3.0, burst_size=5),
        "/api/upload/": RateLimitConfig(requests_per_second=1.0, burst_size=3),
    },
    exclude_paths=["/health", "/metrics"],
)
```

A request to `/api/auth/login` matches the `/api/auth/` config. If no path config matches, the default settings are used.

## Rate limit headers

When `include_headers=True` (default), responses include:

| Header | Description |
|---|---|
| `X-RateLimit-Limit` | Bucket capacity (burst size). |
| `X-RateLimit-Remaining` | Approximate remaining tokens. |

When rate limited (429), responses also include:

| Header | Description |
|---|---|
| `Retry-After` | Seconds until the next request is allowed. |

## Key extraction

By default, rate limiting is keyed by the client's direct IP address from the ASGI scope. The `X-Forwarded-For` header is **not** trusted by default to prevent IP spoofing.

### Behind a reverse proxy

Use `create_key_extractor` with trusted proxy IPs to safely extract the original client IP:

```python
from pykour.middleware import RateLimitMiddleware, create_key_extractor

app.add_middleware(
    RateLimitMiddleware,
    key_extractor=create_key_extractor(
        trusted_proxies={"127.0.0.1", "::1"}
    ),
)
```

When the immediate client IP is in `trusted_proxies`, the first IP from `X-Forwarded-For` is used. CIDR notation is not supported; use exact IP addresses.

### Custom key extraction

Provide any callable that takes an ASGI scope and returns a string:

```python
def key_by_api_key(scope):
    """Rate limit by API key header."""
    headers = dict(scope.get("headers", []))
    api_key = headers.get(b"x-api-key", b"anonymous").decode()
    return api_key

app.add_middleware(
    RateLimitMiddleware,
    key_extractor=key_by_api_key,
)
```

## Custom storage backend

Implement the `RateLimitStorage` abstract class for shared storage (e.g., Redis):

```python
from pykour.middleware import RateLimitStorage

class RedisStorage(RateLimitStorage):
    async def get_tokens(self, key: str) -> tuple[float, float] | None:
        """Return (tokens, last_refill_time) or None."""
        ...

    async def set_tokens(self, key: str, tokens: float, last_refill: float) -> None:
        """Store token count and last refill time."""
        ...

    async def cleanup(self) -> None:
        """Remove expired entries."""
        ...

app.add_middleware(
    RateLimitMiddleware,
    storage=RedisStorage(),
)
```

## 429 response format

When a request is rate limited, the response body is JSON:

```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded. Please try again later.",
  "retry_after": 1.5
}
```

---
**See also:** [JWT Authentication](./jwt-auth.md) · [Security Headers](./security-headers.md) · [Middleware Overview](./index.md)
[← Back to Home](../index.md)
