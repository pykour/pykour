---
title: Testing
parent: Advanced
nav_order: 3
---

# Testing
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

Pykour provides a `TestClient` for testing ASGI applications without running an HTTP server. Tests execute requests directly against the application, making them fast and reliable.

## TestClient

The async `TestClient` is the primary testing interface:

```python
import pytest
from pykour import Pykour
from pykour.testing import TestClient

app = Pykour(routes_dir="routes")
client = TestClient(app)

@pytest.mark.asyncio
async def test_get_users():
    response = await client.get("/users")
    assert response.status_code == 200
    assert "users" in response.json()
```

### Constructor

```python
TestClient(
    app: ASGIApp,
    base_url: str = "http://testserver",
    default_headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    *,
    follow_redirects: bool = False,
    max_redirects: int = 10,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `app` | `ASGIApp` | -- | The ASGI application to test. |
| `base_url` | `str` | `"http://testserver"` | Base URL for requests. |
| `default_headers` | `dict` | `None` | Headers included in every request. |
| `cookies` | `dict` | `None` | Initial cookies. |
| `follow_redirects` | `bool` | `False` | Automatically follow redirects. |
| `max_redirects` | `int` | `10` | Maximum number of redirects to follow. |

### HTTP Methods

All methods return a `TestResponse` and accept the same keyword arguments:

```python
response = await client.get("/path", params={"q": "test"})
response = await client.post("/path", json={"name": "Alice"})
response = await client.put("/path", json={"name": "Bob"})
response = await client.patch("/path", json={"age": 30})
response = await client.delete("/path")
response = await client.head("/path")
response = await client.options("/path")
```

### Common Request Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `headers` | `dict[str, str]` | Request headers. |
| `params` | `dict[str, Any]` | Query parameters. |
| `json` | `Any` | JSON body (auto-serialized). |
| `data` | `bytes \| str` | Raw body data. |
| `content_type` | `str` | Content-Type header. |
| `cookies` | `dict[str, str]` | Cookies for this request. |
| `if_none_match` | `str` | ETag for conditional GET (304 support). |
| `if_modified_since` | `str` | Date for conditional GET. |

### Multipart Upload

```python
response = await client.post_multipart(
    "/upload",
    form_data={"description": "Test file"},
    files={"avatar": ("test.png", b"...image data...", "image/png")},
)
```

### WebSocket Testing

```python
async with client.websocket_connect("/ws/chat") as ws:
    await ws.send_text("Hello")
    message = await ws.receive_text()
    assert message == "Echo: Hello"
```

## TestResponse

All requests return a `TestResponse` object with the following attributes and methods:

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `status_code` | `int` | HTTP status code. |
| `headers` | `dict[str, str]` | Response headers (lowercase keys). |
| `body` | `bytes` | Raw response body. |
| `text` | `str` | Body decoded as UTF-8 text. |
| `is_success` | `bool` | `True` if 2xx status. |
| `is_redirect` | `bool` | `True` if 3xx status. |
| `is_client_error` | `bool` | `True` if 4xx status. |
| `is_server_error` | `bool` | `True` if 5xx status. |
| `cookies` | `dict[str, str]` | Parsed Set-Cookie headers. |
| `etag` | `str \| None` | ETag header value. |
| `last_modified` | `str \| None` | Last-Modified header value. |
| `cache_control` | `dict` | Parsed Cache-Control directives. |

### Methods

```python
# Parse JSON
data = response.json()

# Get header (case-insensitive)
value = response.get_header("Content-Type")
```

### Fluent Assertions

`TestResponse` supports method chaining for assertions:

```python
response = await client.get("/users/1")
(
    response
    .assert_status(200)
    .assert_header("content-type", "application/json")
    .assert_json_contains("name", "Alice")
    .assert_json_equals({"name": "Alice", "id": 1})
)
```

| Method | Description |
|--------|-------------|
| `assert_status(code)` | Assert status code matches. |
| `assert_header(name, value=None)` | Assert header exists (and optionally matches value). |
| `assert_json_equals(expected)` | Assert full JSON body equality. |
| `assert_json_contains(key, value=None)` | Assert JSON contains key (supports dot notation). |

## AuthTestClient

The `AuthTestClient` extends `TestClient` with JWT authentication support for testing protected endpoints:

```python
from pykour.testing import AuthTestClient

client = AuthTestClient(app, secret_key="my-secret")

# Authenticate with default user
client.authenticate(sub="user-1", scopes=["read", "write"])

# All subsequent requests include the JWT Authorization header
response = await client.get("/protected")
assert response.status_code == 200

# Logout to remove auth headers
client.logout()
response = await client.get("/protected")
assert response.status_code == 401
```

### Constructor

```python
AuthTestClient(
    app: ASGIApp,
    *,
    secret_key: str = "test-secret-key",
    **kwargs,  # Passed to TestClient
)
```

### `authenticate` Method

```python
client.authenticate(
    payload: dict | None = None,  # Custom JWT payload
    *,
    scopes: list[str] | None = None,
    roles: list[str] | None = None,
    sub: str = "test-user",
    expires_in: int = 3600,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `payload` | `dict` | `None` | Custom JWT payload (merged with other args). |
| `scopes` | `list[str]` | `None` | Scopes to include in the token. |
| `roles` | `list[str]` | `None` | Roles to include in the token. |
| `sub` | `str` | `"test-user"` | Subject claim. |
| `expires_in` | `int` | `3600` | Token expiration in seconds. |

Returns `self` for method chaining:

```python
response = await client.authenticate(sub="admin", scopes=["admin"]).get("/admin")
```

## SyncTestClient

For tests that don't use `pytest-asyncio`, use the synchronous wrapper:

```python
from pykour.testing import SyncTestClient

client = SyncTestClient(app)

def test_get_users():
    response = client.get("/users")
    assert response.status_code == 200
```

The `SyncTestClient` has the same API as `TestClient` but all methods are synchronous. It accepts the same constructor parameters.

## Redirect Following

Enable automatic redirect following:

```python
client = TestClient(app, follow_redirects=True, max_redirects=5)

# Will follow 301/302/303 redirects automatically
response = await client.post("/old-path", json={"data": "value"})
# response is from the final destination
```

POST/PUT/PATCH requests with 301/302/303 responses are automatically converted to GET per RFC 7231.

## Cookie Management

Cookies are automatically managed across requests:

```python
client = TestClient(app, cookies={"session": "abc123"})

# Server-set cookies are stored in the cookie jar
response = await client.post("/login", json={"user": "admin"})
# Subsequent requests include cookies from the jar
response = await client.get("/dashboard")
```

Access the cookie jar directly:

```python
client.cookie_jar.set("custom", "value")
```

---

{: .fs-2 .text-muted }
Pykour Documentation
