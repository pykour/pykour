---
title: Content Type
parent: Middleware
nav_order: 9
---

# Content Type

`ContentTypeMiddleware` validates the `Content-Type` header of incoming requests, rejecting requests with unsupported media types. This prevents handlers from receiving unexpected content formats.

## Basic usage

```python
from pykour import Pykour
from pykour.middleware import ContentTypeMiddleware

app = Pykour()

app.add_middleware(ContentTypeMiddleware)  # Default: only "application/json"
```

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `allowed_types` | `Sequence[str]` | `("application/json",)` | Allowed Content-Type values. Supports wildcards. |
| `require_content_type` | `bool` | `True` | Reject requests with a body but no `Content-Type` header. |
| `safe_methods` | `Sequence[str]` | `("GET", "HEAD", "OPTIONS", "TRACE")` | HTTP methods to skip validation (no body expected). |
| `exclude_paths` | `Sequence[str]` | `()` | Paths to exclude from validation. |

## Wildcard support

Use wildcards to accept groups of content types:

```python
app.add_middleware(
    ContentTypeMiddleware,
    allowed_types=[
        "application/json",
        "application/*",       # Any application type
        "text/*",              # Any text type
        "*/*",                 # Accept all types
    ],
)
```

## Multiple content types

```python
app.add_middleware(
    ContentTypeMiddleware,
    allowed_types=[
        "application/json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
    ],
)
```

## Missing Content-Type handling

By default, requests with a body but no `Content-Type` header are rejected. Disable this check with:

```python
app.add_middleware(
    ContentTypeMiddleware,
    require_content_type=False,
)
```

## Safe methods

Safe methods (methods that typically have no request body) are skipped by default. Customize the list:

```python
app.add_middleware(
    ContentTypeMiddleware,
    safe_methods=["GET", "HEAD", "OPTIONS"],  # TRACE no longer safe
)
```

## Error response

When validation fails, the middleware returns a `415 Unsupported Media Type` response.

---
**See also:** [Request Size Limit](./request-size-limit.md) · [Middleware Overview](./index.md)
[← Back to Home](../index.md)
