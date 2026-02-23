---
title: CSRF Protection
parent: Middleware
nav_order: 3
---

# CSRF Protection

`CSRFMiddleware` protects against Cross-Site Request Forgery attacks using the double-submit cookie pattern. A CSRF token is set as a cookie and must be sent back in a request header for non-safe HTTP methods.

## Basic usage

```python
from pykour import Pykour
from pykour.middleware import CSRFMiddleware

app = Pykour()

app.add_middleware(CSRFMiddleware)
```

## How it works

1. The middleware sets a `csrf_token` cookie on every response
2. For non-safe methods (`POST`, `PUT`, `DELETE`, `PATCH`), the middleware checks that the request includes an `X-CSRF-Token` header whose value matches the cookie
3. If the tokens do not match or are missing, the middleware returns a `403 Forbidden` response

Safe methods (`GET`, `HEAD`, `OPTIONS`, `TRACE`) are not checked.

## Client-side integration

The cookie is not `HttpOnly` by default, so JavaScript can read it:

```javascript
// Read the CSRF token from the cookie
function getCsrfToken() {
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  return match ? match[1] : null;
}

// Include the token in requests
fetch("/api/data", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-CSRF-Token": getCsrfToken(),
  },
  body: JSON.stringify({ key: "value" }),
});
```

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `cookie_name` | `str` | `"csrf_token"` | Name of the CSRF cookie. |
| `header_name` | `str` | `"X-CSRF-Token"` | Request header that must contain the token. |
| `cookie_path` | `str` | `"/"` | Cookie path. |
| `cookie_domain` | `str \| None` | `None` | Cookie domain. |
| `cookie_secure` | `bool` | `False` | Require HTTPS for the cookie. |
| `cookie_httponly` | `bool` | `False` | HttpOnly flag. Should be `False` so JavaScript can read the token. |
| `cookie_samesite` | `str` | `"Lax"` | SameSite cookie policy. |
| `cookie_max_age` | `int` | `86400` | Cookie max age in seconds (24 hours). |
| `token_bytes` | `int` | `32` | Token length in bytes. |
| `exclude_paths` | `Sequence[str]` | `()` | Paths to exclude from CSRF protection. |
| `exclude_methods` | `Sequence[str]` | `()` | Additional methods to exclude (beyond safe methods). |

## Production configuration

```python
app.add_middleware(
    CSRFMiddleware,
    cookie_secure=True,         # HTTPS only
    cookie_samesite="Strict",   # Strict same-site policy
    cookie_domain=".example.com",
    exclude_paths=["/api/webhooks"],  # Skip for webhook endpoints
)
```

## Excluding paths and methods

```python
app.add_middleware(
    CSRFMiddleware,
    exclude_paths=["/api/webhooks", "/api/public"],
    exclude_methods=["PUT"],  # Also exclude PUT from CSRF checks
)
```

The `exclude_methods` parameter adds to the default safe methods (`GET`, `HEAD`, `OPTIONS`, `TRACE`).

---
**See also:** [CORS](./cors.md) · [Security Headers](./security-headers.md) · [Middleware Overview](./index.md)
[← Back to Home](../index.md)
