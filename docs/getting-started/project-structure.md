---
title: Project Structure
parent: Getting Started
nav_order: 3
---

# Project Structure

Pykour uses **file-based routing** inspired by Next.js. The directory layout of your `routes/` folder directly maps to URL paths.

## Recommended layout

```
my-app/
├── app.py                     # Application entry point
├── pykour.toml                # Optional configuration file
├── routes/
│   ├── route.py               # GET /
│   ├── health/
│   │   └── route.py           # GET /health
│   └── api/
│       └── users/
│           ├── route.py        # GET|POST /api/users
│           └── [id]/
│               └── route.py    # GET|PUT|DELETE /api/users/{id}
├── services/                   # Business logic, DI services
├── schemas/                    # Request/response schemas
└── migrations/                 # Database migration files
```

## app.py

The entry point creates a `Pykour` instance and optionally configures database connections, middleware, and other options:

```python
from pathlib import Path
from pykour import Pykour

app = Pykour(routes_dir=Path(__file__).parent / "routes")
```

Key `Pykour()` parameters:

| Parameter | Description |
|-----------|-------------|
| `routes_dir` | Path to the routes directory. Defaults to `routes/` next to the caller file. |
| `database` | A `Database` instance for DI and query builder access. |
| `cache` | A `CacheStorage` instance for response/data caching. |
| `debug` | Enable debug mode (detailed tracebacks). |
| `config_file` | Path to `pykour.toml` configuration file. |

## File-based routing rules

### Basic routes

Each `route.py` file maps to a URL path based on its location in the `routes/` directory:

| File | URL Path |
|------|----------|
| `routes/route.py` | `/` |
| `routes/about/route.py` | `/about` |
| `routes/api/users/route.py` | `/api/users` |

### Dynamic segments

Wrap a directory name in square brackets to create a dynamic path parameter:

| File | URL Path | Parameter |
|------|----------|-----------|
| `routes/api/users/[id]/route.py` | `/api/users/{id}` | `id` |
| `routes/api/posts/[post_id]/comments/[comment_id]/route.py` | `/api/posts/{post_id}/comments/{comment_id}` | `post_id`, `comment_id` |

Access dynamic parameters in your handler using `Path()`:

```python
from pykour import Path

async def get(id: int = Path()):
    return {"user_id": id}
```

### HTTP method handlers

Each `route.py` exports async functions named after HTTP methods:

```python
async def get():
    """Handles GET requests."""
    return {"items": []}

async def post():
    """Handles POST requests."""
    return {"created": True}

async def put():
    """Handles PUT requests."""
    ...

async def delete():
    """Handles DELETE requests."""
    ...

async def patch():
    """Handles PATCH requests."""
    ...
```

Only the methods you define are registered. A `route.py` with only `get` and `post` will return `405 Method Not Allowed` for other HTTP methods on that path.

## Configuration file (pykour.toml)

Pykour automatically discovers a `pykour.toml` in the current working directory. This file lets you configure middleware, database connections, and other settings without modifying Python code:

```toml
[app]
debug = false

[database]
url = "sqlite:///app.db"
```

See the [Configuration Reference](../advanced/cli.md) for all available options.

## Next steps

- Follow the [Quickstart](quickstart.md) to build your first app.
- Learn about [Schema Validation](../core/schema-validation.md) for request bodies.
- Set up a [Database](../database/index.md) with migrations.

---

**See also:** [Quickstart](quickstart.md) · [Core Documentation](../core/index.md)
[← Back to Home](../index.md)
