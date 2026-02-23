---
title: Home
nav_order: 1
---

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
{: .text-gamma }

| Page | Description |
|:-----|:------------|
| [Installation](getting-started/installation) | Install Pykour and prerequisites |
| [Quickstart](getting-started/quickstart) | Build your first app step by step |
| [Project Structure](getting-started/project-structure) | Recommended directory layout and conventions |

### Core
{: .text-gamma }

| Page | Description |
|:-----|:------------|
| [Routing](core/routing) | File-based and decorator-based route definitions |
| [Request](core/request) | Access headers, query params, body, and client info |
| [Response](core/response) | JSON, HTML, streaming, and custom responses |
| [Parameter Injection](core/parameter-injection) | Path, Query, Body, and Depends markers |
| [Schema Validation](core/schema-validation) | Define schemas with Field constraints and validators |
| [Dependency Injection](core/dependency-injection) | Service container, scopes, and Depends |
| [Exception Handling](core/exception-handling) | Custom exception handlers and error responses |
| [WebSocket](core/websocket) | WebSocket connections and message handling |

### Middleware
{: .text-gamma }

| Page | Description |
|:-----|:------------|
| [Overview](middleware/) | Middleware architecture and custom middleware |
| [JWT Auth](middleware/jwt-auth) | JSON Web Token authentication and authorization |
| [CORS](middleware/cors) | Cross-Origin Resource Sharing configuration |
| [CSRF](middleware/csrf) | Cross-Site Request Forgery protection |
| [Rate Limiting](middleware/rate-limiting) | Request rate limiting per client |
| [Security Headers](middleware/security-headers) | HTTP security headers (CSP, HSTS, etc.) |
| [Logging](middleware/logging) | Request/response logging |
| [Tracing](middleware/tracing) | Distributed tracing with trace IDs |
| [Request Size Limit](middleware/request-size-limit) | Maximum request body size enforcement |
| [Content Type](middleware/content-type) | Content type validation and negotiation |

### Database
{: .text-gamma }

| Page | Description |
|:-----|:------------|
| [Overview](database/) | Database setup and driver configuration |
| [Query Builder](database/query-builder) | Fluent API for SELECT, INSERT, UPDATE, DELETE |
| [Transactions](database/transactions) | Transaction management and isolation levels |
| [Migrations](database/migrations) | Schema migrations and version control |
| [Access Policies](database/access-policies) | Row-level security and access control |

### Advanced
{: .text-gamma }

| Page | Description |
|:-----|:------------|
| [Overview](advanced/) | Advanced features summary |
| [Caching](advanced/caching) | Response caching strategies |
| [OpenAPI](advanced/openapi) | Automatic OpenAPI schema generation |
| [Testing](advanced/testing) | TestClient and SyncTestClient usage |
| [Configuration](advanced/configuration) | Environment variables and config files |
| [CLI](advanced/cli) | Command-line interface reference |
| [Metrics](advanced/metrics) | Application metrics and monitoring |
| [Health Checks](advanced/health-checks) | Health and readiness endpoints |
| [CRUD](advanced/crud) | Automatic CRUD route generation |
| [Response Decorators](advanced/response-decorators) | Headers, status codes, and response metadata |

### Reference
{: .text-gamma }

| Page | Description |
|:-----|:------------|
| [Exceptions](reference/exceptions) | Built-in exception classes reference |
| [Changelog](reference/changelog) | Version history and release notes |
