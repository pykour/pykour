# Pykour Documentation

Pykour is a lightweight ASGI web framework for Python 3.13+ that brings **Next.js-style file-based routing** to Python. It includes built-in schema validation, dependency injection, database support (SQLite, PostgreSQL, MySQL), and a rich middleware stack.

## Quick Install

```bash
pip install pykour
```

## Hello World

```python
from pykour import Pykour

app = Pykour()

@app.get("/")
async def hello():
    return {"message": "Hello, World!"}
```

Run the application:

```bash
pykour run main:app
```

## File-Based Routing

Pykour discovers routes from your project's `routes/` directory automatically:

```
routes/
  route.py          -> /
  api/
    users/
      route.py      -> /api/users
      [id]/
        route.py    -> /api/users/{id}
```

Each `route.py` exports async handler functions named after HTTP methods:

```python
# routes/api/users/route.py

async def get():
    return [{"id": 1, "name": "Alice"}]

async def post(user: UserSchema = Body()):
    return {"id": 2, **user.to_dict()}
```

## Documentation Map

### Getting Started

| Page | Description |
|:-----|:------------|
| [Installation](getting-started/installation.md) | Install Pykour and prerequisites |
| [Quickstart](getting-started/quickstart.md) | Build your first app step by step |
| [Project Structure](getting-started/project-structure.md) | Recommended directory layout and conventions |

### Core

| Page | Description |
|:-----|:------------|
| [Routing](core/routing.md) | File-based and decorator-based route definitions |
| [Request](core/request.md) | Access headers, query params, body, and client info |
| [Response](core/response.md) | JSON, HTML, streaming, and custom responses |
| [Parameter Injection](core/parameter-injection.md) | Path, Query, Body, and Depends markers |
| [Schema Validation](core/schema-validation.md) | Define schemas with Field constraints and validators |
| [Dependency Injection](core/dependency-injection.md) | Service container, scopes, and Depends |
| [Exception Handling](core/exception-handling.md) | Custom exception handlers and error responses |
| [WebSocket](core/websocket.md) | WebSocket connections and message handling |

### Middleware

| Page | Description |
|:-----|:------------|
| [Overview](middleware/index.md) | Middleware architecture and custom middleware |
| [JWT Auth](middleware/jwt-auth.md) | JSON Web Token authentication and authorization |
| [CORS](middleware/cors.md) | Cross-Origin Resource Sharing configuration |
| [CSRF](middleware/csrf.md) | Cross-Site Request Forgery protection |
| [Rate Limiting](middleware/rate-limiting.md) | Request rate limiting per client |
| [Security Headers](middleware/security-headers.md) | HTTP security headers (CSP, HSTS, etc.) |
| [Logging](middleware/logging.md) | Request/response logging |
| [Tracing](middleware/tracing.md) | Distributed tracing with trace IDs |
| [Request Size Limit](middleware/request-size-limit.md) | Maximum request body size enforcement |
| [Content Type](middleware/content-type.md) | Content type validation and negotiation |

### Database

| Page | Description |
|:-----|:------------|
| [Overview](database/index.md) | Database setup and driver configuration |
| [Query Builder](database/query-builder.md) | Fluent API for SELECT, INSERT, UPDATE, DELETE |
| [Transactions](database/transactions.md) | Transaction management and isolation levels |
| [Migrations](database/migrations.md) | Schema migrations and version control |
| [Access Policies](database/access-policies.md) | Row-level security and access control |

### Advanced

| Page | Description |
|:-----|:------------|
| [Overview](advanced/index.md) | Advanced features summary |
| [Caching](advanced/caching.md) | Response caching strategies |
| [OpenAPI](advanced/openapi.md) | Automatic OpenAPI schema generation |
| [Testing](advanced/testing.md) | TestClient and SyncTestClient usage |
| [Configuration](advanced/configuration.md) | Environment variables and config files |
| [CLI](advanced/cli.md) | Command-line interface reference |
| [Metrics](advanced/metrics.md) | Application metrics and monitoring |
| [Health Checks](advanced/health-checks.md) | Health and readiness endpoints |
| [CRUD](advanced/crud.md) | Automatic CRUD route generation |
| [Response Decorators](advanced/response-decorators.md) | Headers, status codes, and response metadata |

### Reference

| Page | Description |
|:-----|:------------|
| [Exceptions](reference/exceptions.md) | Built-in exception classes reference |
| [Changelog](reference/changelog.md) | Version history and release notes |
