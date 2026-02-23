---
title: Middleware
nav_order: 4
has_children: true
---

# Middleware

Middleware intercepts every HTTP request and response, letting you add cross-cutting concerns such as authentication, logging, and security headers without touching individual route handlers.

## How middleware works

Pykour middleware follows the ASGI middleware pattern. Each middleware wraps the application and can:

1. Inspect or modify the incoming request (ASGI scope)
2. Call the next middleware or the application itself
3. Inspect or modify the outgoing response

```
Client Request
  → Middleware A (before)
    → Middleware B (before)
      → Route Handler
    ← Middleware B (after)
  ← Middleware A (after)
Client Response
```

Middleware added **later** wraps middleware added **earlier**. This means the last middleware added is the outermost layer and runs first on the request path.

## Adding middleware

### Class-based middleware

Use `app.add_middleware()` to register a class-based middleware:

```python
from pykour import Pykour
from pykour.middleware import CORSMiddleware

app = Pykour()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://example.com"],
    allow_methods=["GET", "POST"],
)
```

All keyword arguments are forwarded to the middleware constructor. The `app` parameter is injected automatically.

### Function-based middleware

Use the `@app.middleware` decorator for simple middleware:

```python
from pykour import Pykour
from pykour.request import Request
from pykour.response import Response

app = Pykour()

@app.middleware
async def timing_middleware(request: Request, call_next) -> Response:
    import time
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    print(f"{request.method} {request.path} took {duration:.3f}s")
    return response
```

The `call_next` function invokes the next middleware in the chain and returns a `Response` object.

## Creating custom middleware

Extend `BaseMiddleware` and implement the `__call__` method:

```python
from pykour.middleware import BaseMiddleware, Scope, Receive, Send

class MyMiddleware(BaseMiddleware):
    def __init__(self, app, *, custom_option: str = "default") -> None:
        super().__init__(app)
        self.custom_option = custom_option

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Pre-processing
        print(f"Option: {self.custom_option}, Path: {scope['path']}")

        # Call next middleware / application
        await self.app(scope, receive, send)

        # Post-processing (response already sent at this point)
```

### Path exclusion

Most built-in middleware accepts an `exclude_paths` parameter. The `BaseMiddleware.should_process_path()` helper method handles prefix matching:

```python
async def __call__(self, scope, receive, send):
    path = scope.get("path", "/")
    if not self.should_process_path(path, self.exclude_paths):
        await self.app(scope, receive, send)
        return
    # ... process request
```

## Built-in middleware

| Middleware | Description | Import |
|---|---|---|
| [JWTAuthMiddleware](./jwt-auth.md) | JWT bearer token authentication with key rotation and scopes | `pykour.middleware` |
| [CORSMiddleware](./cors.md) | Cross-Origin Resource Sharing headers | `pykour.middleware` |
| [CSRFMiddleware](./csrf.md) | CSRF token protection via double-submit cookie | `pykour.middleware` |
| [RateLimitMiddleware](./rate-limiting.md) | Token bucket rate limiting with per-path configuration | `pykour.middleware` |
| [SecurityHeadersMiddleware](./security-headers.md) | HSTS, CSP, X-Frame-Options, and other security headers | `pykour.middleware` |
| [LoggingMiddleware](./logging.md) | Structured access logging in text or JSON format | `pykour.middleware` |
| [TraceMiddleware](./tracing.md) | Distributed tracing with W3C Trace Context support | `pykour.middleware` |
| [RequestSizeLimitMiddleware](./request-size-limit.md) | Request body size enforcement | `pykour.middleware` |
| [ContentTypeMiddleware](./content-type.md) | Content-Type header validation | `pykour.middleware` |

---
**See also:** [JWT Authentication](./jwt-auth.md) · [CORS](./cors.md) · [Rate Limiting](./rate-limiting.md)
[← Back to Home](../index.md)
