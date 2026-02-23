# Request Size Limit

`RequestSizeLimitMiddleware` enforces maximum request body sizes to protect your application from oversized payloads. It supports both upfront `Content-Length` checking and streaming body size enforcement, with per-content-type limits.

## Basic usage

```python
from pykour import Pykour
from pykour.middleware import RequestSizeLimitMiddleware

app = Pykour()

app.add_middleware(RequestSizeLimitMiddleware)  # Default: 1 MB
```

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `max_size` | `int` | `1048576` (1 MB) | Maximum request body size in bytes. |
| `max_size_by_content_type` | `dict[str, int] \| None` | `None` | Content-Type specific size limits. |
| `exclude_paths` | `Sequence[str]` | `()` | Paths to exclude from size checking. |
| `check_content_length` | `bool` | `True` | Check `Content-Length` header upfront. |
| `check_body_size` | `bool` | `True` | Check actual body size during streaming. |

## Custom size limits

```python
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_size=5 * 1024 * 1024,  # 5 MB default
)
```

## Per-content-type limits

Set different limits based on the request's `Content-Type`:

```python
app.add_middleware(
    RequestSizeLimitMiddleware,
    max_size=1 * 1024 * 1024,  # 1 MB default
    max_size_by_content_type={
        "multipart/form-data": 50 * 1024 * 1024,    # 50 MB for file uploads
        "application/json": 256 * 1024,               # 256 KB for JSON
        "application/octet-stream": 100 * 1024 * 1024, # 100 MB for binary
    },
)
```

## Size checking modes

The middleware provides two layers of protection:

### Content-Length check (`check_content_length`)

Rejects requests immediately if the `Content-Length` header exceeds the limit. This is efficient but relies on the client sending an accurate header.

### Body size check (`check_body_size`)

Monitors the actual body data as it streams in. This catches requests that have no `Content-Length` header or an inaccurate one.

Both checks are enabled by default. You can disable either:

```python
app.add_middleware(
    RequestSizeLimitMiddleware,
    check_content_length=True,   # Fast upfront rejection
    check_body_size=False,       # Skip streaming check
)
```

## Excluding paths

```python
app.add_middleware(
    RequestSizeLimitMiddleware,
    exclude_paths=["/upload", "/api/import"],
)
```

## Error handling

When a request exceeds the size limit, the middleware returns a `413 Payload Too Large` response. The `RequestTooLargeError` exception is also available for custom handling:

```python
from pykour.middleware import RequestTooLargeError
```

---
**See also:** [Content Type](./content-type.md) · [Middleware Overview](./index.md)
[← Back to Home](../index.md)
