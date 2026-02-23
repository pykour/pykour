---
title: JWT Authentication
parent: Middleware
nav_order: 1
---

# JWT Authentication

`JWTAuthMiddleware` provides JSON Web Token (JWT) authentication using the `Authorization: Bearer <token>` header. It supports key rotation, scope-based authorization, and path exclusion.

## Basic usage

```python
from pykour import Pykour
from pykour.middleware import JWTAuthMiddleware

app = Pykour()

app.add_middleware(
    JWTAuthMiddleware,
    secret_key="your-secret-key",
    exclude_paths=["/health", "/login"],
)
```

Authenticated requests set `scope["user"]` (accessible as `request.user`) to the decoded JWT payload.

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `secret_key` | `str \| None` | `None` | Secret key for token verification. Use `secret_keys` for key rotation. |
| `secret_keys` | `Sequence[str] \| None` | `None` | List of keys for verification. First key is used for signing. |
| `algorithm` | `str` | `"HS256"` | JWT signing algorithm. Only HS256 is supported. |
| `exclude_paths` | `Sequence[str]` | `()` | Paths to skip authentication. |
| `auto_error` | `bool` | `True` | If `True`, return 401 for invalid tokens. If `False`, continue without user data. |

You must provide exactly one of `secret_key` or `secret_keys`. Providing both or neither raises `ValueError`.

## Key rotation

Use `secret_keys` to rotate signing keys without downtime. The first key signs new tokens; all keys are tried during verification:

```python
app.add_middleware(
    JWTAuthMiddleware,
    secret_keys=[
        "new-secret-key",   # Used for signing
        "old-secret-key",   # Still accepted for verification
    ],
)
```

To rotate keys:

1. Add the new key at the beginning of `secret_keys`
2. Deploy the change -- new tokens use the new key, old tokens still verify
3. After all old tokens expire, remove the old key

## Creating tokens

The `create_jwt_token` helper creates HS256 JWT tokens:

```python
from pykour.middleware import create_jwt_token

token = create_jwt_token(
    payload={"sub": "user123", "scope": "users:read users:write"},
    secret_key="your-secret-key",
    expires_in=3600,  # 1 hour
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `payload` | `dict[str, Any]` | required | Token payload data. |
| `secret_key` | `str` | required | Secret key for signing. |
| `algorithm` | `str` | `"HS256"` | Signing algorithm. |
| `expires_in` | `int \| None` | `None` | Expiration in seconds from now. |

You can set expiration either via `expires_in` or by including `"exp"` in the payload, but not both.

## Scope-based authorization

The `require_scope` decorator enforces JWT scopes on route handlers:

```python
from pykour.middleware import require_scope
from pykour.request import Request
from pykour.response import JSONResponse

@require_scope("users:read")
async def get(request: Request) -> JSONResponse:
    return JSONResponse({"users": []})

@require_scope("admin", "superuser", match="any")
async def delete(request: Request) -> JSONResponse:
    return JSONResponse({"deleted": True})

@require_scope("read", "write", match="all")
async def update(request: Request) -> JSONResponse:
    return JSONResponse({"updated": True})
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `*scopes` | `str` | required | One or more required scope strings. |
| `claim` | `str` | `"scope"` | JWT claim name containing the scopes. |
| `match` | `"any" \| "all"` | `"any"` | `"any"` requires at least one scope; `"all"` requires every scope. |

Scopes in the JWT payload can be a space-separated string (e.g., `"users:read users:write"`) or a list.

If the user is not authenticated, `require_scope` raises `UnauthorizedException` (401). If scopes are insufficient, it raises `ForbiddenException` (403).

`require_roles` is an alias for `require_scope`.

## Accessing user data

After successful authentication, the decoded payload is available on the request:

```python
async def get(request: Request) -> JSONResponse:
    user = request.user  # Decoded JWT payload dict
    user_id = user["sub"]
    return JSONResponse({"user_id": user_id})
```

## OpenAPI integration

`require_scope` automatically attaches `__openapi_security__` metadata to decorated handlers, enabling automatic security scheme generation in OpenAPI documentation.

---
**See also:** [CORS](./cors.md) · [Middleware Overview](./index.md)
[← Back to Home](../index.md)
