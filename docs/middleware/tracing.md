# Tracing

`TraceMiddleware` adds distributed tracing support by managing trace IDs across requests. It follows the W3C Trace Context specification, extracting trace IDs from incoming `traceparent` headers or generating new ones.

## Basic usage

```python
from pykour import Pykour
from pykour.middleware import TraceMiddleware

app = Pykour()

app.add_middleware(TraceMiddleware)
```

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `response_header` | `str` | `"X-Trace-ID"` | Header name for the trace ID in responses. |

## How it works

1. **Incoming request**: The middleware checks for a `traceparent` header (W3C Trace Context format). If present, the trace ID is extracted from it. Otherwise, a new UUID trace ID is generated.
2. **Scope injection**: The trace ID is stored in `scope["trace_id"]`, making it available to other middleware and handlers.
3. **Context variable**: The trace ID is set in a context variable accessible via `get_trace_id()`.
4. **Response header**: The trace ID is added to the response as `X-Trace-ID` (configurable).

## Accessing the trace ID

### In route handlers

```python
from pykour.request import Request
from pykour.response import JSONResponse

async def get(request: Request) -> JSONResponse:
    trace_id = request.scope.get("trace_id")
    return JSONResponse({"trace_id": trace_id})
```

### In other middleware

```python
from pykour.middleware import BaseMiddleware, Scope, Receive, Send

class MyMiddleware(BaseMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        trace_id = scope.get("trace_id")  # Set by TraceMiddleware
        print(f"Processing request with trace ID: {trace_id}")
        await self.app(scope, receive, send)
```

## W3C Trace Context

The middleware parses the standard `traceparent` header format:

```
traceparent: 00-<trace-id>-<parent-id>-<trace-flags>
```

For example:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

The 32-character `trace-id` portion is extracted and used as the trace ID.

## Custom response header

```python
app.add_middleware(
    TraceMiddleware,
    response_header="X-Request-ID",
)
```

## Middleware ordering

Place `TraceMiddleware` early in the middleware stack (add it first or second) so that other middleware such as `LoggingMiddleware` can use the trace ID:

```python
app.add_middleware(TraceMiddleware)
app.add_middleware(LoggingMiddleware)
# ... other middleware
```

---
**See also:** [Logging](./logging.md) · [Middleware Overview](./index.md)
[← Back to Home](../index.md)
