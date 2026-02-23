---
title: CORS
parent: Middleware
nav_order: 2
---

# CORS

`CORSMiddleware` handles Cross-Origin Resource Sharing (CORS) by managing preflight requests and adding the appropriate response headers.

## Basic usage

```python
from pykour import Pykour
from pykour.middleware import CORSMiddleware

app = Pykour()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com", "https://app.example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
    max_age=3600,
)
```

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `allow_origins` | `Sequence[str]` | `()` | Allowed origins. Use `"*"` to allow all. Supports wildcard patterns. |
| `allow_methods` | `Sequence[str]` | `("GET",)` | Allowed HTTP methods. |
| `allow_headers` | `Sequence[str]` | `()` | Allowed request headers. |
| `allow_credentials` | `bool` | `False` | Allow credentials (cookies, auth headers). |
| `expose_headers` | `Sequence[str]` | `()` | Headers exposed to the browser. |
| `max_age` | `int` | `600` | Preflight cache duration in seconds. |

## Wildcard origins

You can use wildcard patterns to match multiple subdomains:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://*.example.com"],
)
```

This matches `https://app.example.com`, `https://api.example.com`, etc.

To allow all origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
)
```

**Note:** When `allow_credentials=True`, using `"*"` for origins is generally not recommended by browsers. Use explicit origins or wildcard patterns instead.

## Preflight requests

The middleware automatically handles `OPTIONS` preflight requests. When a browser sends a preflight request, the middleware responds directly with the appropriate CORS headers and a `200` status, without forwarding the request to your application.

## Configuration examples

### Public API

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    max_age=86400,
)
```

### Single-page application

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
    allow_credentials=True,
    expose_headers=["X-Total-Count"],
)
```

---
**See also:** [CSRF Protection](./csrf.md) · [Security Headers](./security-headers.md) · [Middleware Overview](./index.md)
[← Back to Home](../index.md)
