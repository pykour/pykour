# Pykour

A lightweight ASGI web framework for Python 3.13+ with Next.js-style file-based routing.

## Features

- **File-based routing**: Define routes by file structure (like Next.js)
- **Built-in schema validation**: Custom validation system for request bodies
- **Dependency injection**: Service container with `Depends()` marker
- **Database support**: SQLite, PostgreSQL, MySQL with query builder API
- **Middleware**: CORS, JWT auth, rate limiting, security headers, and more

## Installation

```bash
pip install pykour
```

## Quick Start

Create a route file at `routes/route.py`:

```python
async def get():
    return {"message": "Hello, World!"}
```

Run the application:

```bash
pykour run app:app --reload
```

## File-Based Routing

Routes are defined by file structure in a `routes/` directory:

| File Path | Route |
|-----------|-------|
| `routes/route.py` | `/` |
| `routes/api/users/route.py` | `/api/users` |
| `routes/api/users/[id]/route.py` | `/api/users/{id}` |

Each `route.py` exports HTTP method handlers as async functions: `get`, `post`, `put`, `delete`, `patch`.

## License

MIT
