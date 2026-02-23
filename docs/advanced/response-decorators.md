---
title: Response Decorators
parent: Advanced
nav_order: 9
---

# Response Decorators
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

Pykour provides declarative decorators for controlling HTTP response status codes, headers, and conditional responses (ETag, Last-Modified). These decorators also feed into the OpenAPI documentation.

## `@status_code`

Declare the default HTTP status code for a handler response. When the handler returns a response with the default status code (200), the declared status code is applied instead.

```python
from pykour import Request, JSONResponse, Body
from pykour.status_code import status_code

@status_code(201, description="Created")
async def post(request: Request, data: UserSchema = Body()) -> JSONResponse:
    user = await create_user(data)
    return JSONResponse({"id": user.id})
```

If the handler explicitly sets a non-default status code, the explicit value takes precedence:

```python
@status_code(200, description="Success")
@status_code(404, description="Not Found", is_default=False)
async def get(request: Request, id: int = Path()) -> JSONResponse:
    user = await get_user(id)
    if not user:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(user)
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `code` | `int` | -- | HTTP status code. |
| `description` | `str \| None` | `None` | Description for OpenAPI documentation. |
| `is_default` | `bool` | `True` | If `True`, apply this code when response has the default status. If `False`, only for documentation. |

Multiple `@status_code` decorators can be stacked to document multiple possible responses in OpenAPI.

## `@header`

Declare HTTP response headers. Headers are applied after the handler returns. The value can include `{param}` placeholders for dynamic values.

```python
from pykour.header import header

# Static header
@header("X-API-Version", "1.0")
async def get(request: Request) -> JSONResponse:
    return JSONResponse({"data": "value"})
```

### Dynamic Values

Placeholders are resolved from handler keyword arguments first, then from the response body:

```python
# From response body
@header("Location", "/users/{id}")
@status_code(201)
async def post(request: Request) -> JSONResponse:
    return JSONResponse({"id": 123})  # Location: /users/123

# From path parameter
@header("Location", "/users/{user_id}")
@status_code(201)
async def create(request: Request, user_id: int = Path()) -> JSONResponse:
    return JSONResponse({"created": True})
```

### Conditional Headers

Apply headers only on specific status codes:

```python
@header("Location", "/items/{id}", on_status=201)
async def create_item(request: Request) -> JSONResponse:
    item = await create(...)
    return JSONResponse({"id": item.id}, status_code=201)
```

### Stacking Multiple Headers

```python
@header("X-Request-Id", "{request_id}")
@header("X-Correlation-Id", "{correlation_id}")
async def handler(request: Request, request_id: str = Query()) -> JSONResponse:
    return JSONResponse({"ok": True})
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | -- | HTTP header name. |
| `value` | `str` | -- | Header value template. Use `{param}` for dynamic values. |
| `on_status` | `int \| tuple[int, ...] \| None` | `None` | Only apply on specific status code(s). |

## `@etag`

Enable automatic ETag generation and conditional response handling. The ETag is computed from the response body hash.

```python
from pykour.conditional import etag

@etag()
async def get(request: Request, id: int = Path()) -> JSONResponse:
    return JSONResponse({"id": id, "data": "..."})
```

When a client sends an `If-None-Match` header matching the current ETag, the server returns `304 Not Modified` with no body.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `weak` | `bool` | `False` | Generate weak ETag (`W/"..."`) instead of strong ETag. |
| `algorithm` | `str` | `"md5"` | Hash algorithm: `"md5"`, `"sha1"`, or `"sha256"`. |

```python
@etag(weak=True, algorithm="sha256")
async def get_resource(request: Request) -> JSONResponse:
    return JSONResponse({"resource": "data"})
```

## `@last_modified`

Enable Last-Modified header and conditional response handling. When a client sends `If-Modified-Since` and the resource hasn't changed, the server returns `304 Not Modified`.

### Fixed Value

```python
from datetime import datetime
from pykour.conditional import last_modified

@last_modified(value=datetime(2024, 1, 1, 0, 0, 0))
async def get_static(request: Request) -> JSONResponse:
    return JSONResponse({"data": "static content"})
```

### Dynamic from Response Body

Extract the timestamp from a field in the response JSON:

```python
@last_modified(field="updated_at")
async def get_user(request: Request, id: int = Path()) -> JSONResponse:
    user = await get_user_from_db(id)
    return JSONResponse({
        "id": user.id,
        "name": user.name,
        "updated_at": user.updated_at.isoformat(),
    })
```

### Nested Field (dot notation)

```python
@last_modified(field="metadata.modified")
async def get_item(request: Request) -> JSONResponse:
    return JSONResponse({
        "data": "...",
        "metadata": {"modified": "2024-01-15T10:30:00"}
    })
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `value` | `datetime \| None` | `None` | Fixed datetime for Last-Modified header. |
| `field` | `str \| None` | `None` | Response body field to extract timestamp from. Supports dot notation. |
| `format` | `str` | `"%Y-%m-%dT%H:%M:%S"` | Date format for parsing the response field value. |

## Combining Decorators

Decorators can be stacked for rich response behavior:

```python
@status_code(200, description="Success")
@status_code(404, description="Not Found", is_default=False)
@header("X-API-Version", "1.0")
@etag()
@cache(key="user:{id}", ttl=300)
async def get(request: Request, id: int = Path()) -> JSONResponse:
    user = await get_user(id)
    if not user:
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse(user)
```

---

{: .fs-2 .text-muted }
Pykour Documentation
