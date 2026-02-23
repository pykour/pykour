# OpenAPI Documentation

Pykour automatically generates OpenAPI 3.1 documentation from your routes, parameter annotations, and schema definitions. Swagger UI and ReDoc are served as built-in endpoints.

## Default Endpoints

OpenAPI documentation is enabled by default with the following URLs:

| Endpoint | Description |
|----------|-------------|
| `/docs` | Swagger UI interactive documentation |
| `/redoc` | ReDoc documentation |
| `/openapi.json` | Raw OpenAPI JSON schema |

These are available as soon as you create a `Pykour` application with no additional configuration.

## Configuration

### Constructor Parameters

```python
from pykour import Pykour

app = Pykour(
    routes_dir="routes",
    title="My API",
    version="2.0.0",
    description="A sample API built with Pykour",
    docs_url="/docs",         # Set to None to disable Swagger UI
    openapi_url="/openapi.json",  # Set to None to disable OpenAPI JSON
    redoc_url="/redoc",       # Set to None to disable ReDoc
)
```

### Disabling Documentation

```python
app = Pykour(
    routes_dir="routes",
    docs_url=None,
    openapi_url=None,
    redoc_url=None,
)
```

### TOML Configuration

```toml
[openapi]
title = "My API"
version = "2.0.0"
description = "A sample API built with Pykour"
docs_url = "/docs"
openapi_url = "/openapi.json"
redoc_url = "/redoc"

[openapi.contact]
name = "API Support"
email = "support@example.com"
url = "https://example.com/support"

[openapi.license]
name = "MIT"
url = "https://opensource.org/licenses/MIT"

[[openapi.servers]]
url = "https://api.example.com"
description = "Production"

[[openapi.servers]]
url = "http://localhost:8000"
description = "Development"
```

## OpenAPIConfig

The full configuration dataclass:

```python
from pykour.openapi import OpenAPIConfig

config = OpenAPIConfig(
    title="My API",
    version="1.0.0",
    description="API description",
    summary="Short summary",
    terms_of_service="https://example.com/tos",
    contact=ContactInfo(name="Support", email="support@example.com"),
    license=LicenseInfo(name="MIT"),
    servers=[ServerInfo(url="https://api.example.com", description="Production")],
    openapi_version="3.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    redoc_url="/redoc",
    tags=[{"name": "users", "description": "User operations"}],
    security_schemes=None,
    global_security=None,
    include_head_operations=False,
    include_options_operations=False,
)
```

## Security Schemes

### JWT Bearer Authentication

Pykour provides helper functions to configure security schemes:

```python
from pykour import Pykour
from pykour.openapi import jwt_bearer_scheme

app = Pykour(
    routes_dir="routes",
    security_schemes=jwt_bearer_scheme(
        name="bearerAuth",
        description="JWT Bearer token authentication",
        bearer_format="JWT",
    ),
)
```

The `jwt_bearer_scheme` function creates a `SecuritySchemeConfig` with type `"http"` and scheme `"bearer"`.

### API Key Authentication

```python
from pykour.openapi import api_key_scheme

app = Pykour(
    routes_dir="routes",
    security_schemes=api_key_scheme(
        name="apiKeyAuth",
        header_name="X-API-Key",
        description="API key passed in header",
    ),
)
```

### Auto-Generation from JWT Middleware

When you use `require_scope` in your routes without explicitly specifying security schemes, Pykour automatically generates a default Bearer JWT security scheme in the OpenAPI documentation.

### Custom Security Schemes

```python
from pykour.openapi.config import SecuritySchemeConfig

app = Pykour(
    routes_dir="routes",
    security_schemes={
        "bearerAuth": SecuritySchemeConfig(
            type="http",
            scheme="bearer",
            bearer_format="JWT",
            description="JWT authentication",
        ),
        "apiKey": SecuritySchemeConfig(
            type="apiKey",
            name="X-API-Key",
            api_key_in="header",
        ),
    },
    global_security=[{"bearerAuth": []}],
)
```

### SecuritySchemeConfig Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | `Literal["http", "apiKey", "oauth2", "openIdConnect"]` | Security scheme type. |
| `scheme` | `str \| None` | HTTP auth scheme (e.g., `"bearer"`). |
| `bearer_format` | `str \| None` | Bearer token format (e.g., `"JWT"`). |
| `name` | `str \| None` | API key header/query/cookie name. |
| `api_key_in` | `Literal["header", "query", "cookie"] \| None` | Where API key is sent. |
| `flows` | `dict[str, OAuthFlow] \| None` | OAuth2 flows. |
| `open_id_connect_url` | `str \| None` | OpenID Connect discovery URL. |
| `description` | `str \| None` | Description of the scheme. |

## How Routes Are Documented

Pykour automatically extracts the following from your route handlers:

- **Path parameters** from `Path()` annotations
- **Query parameters** from `Query()` annotations
- **Request body** from `Body()` annotations and `Schema` classes
- **Response codes** from `@status_code` decorators
- **Tags** from the route path (first path segment)
- **Operation IDs** generated from path and method
