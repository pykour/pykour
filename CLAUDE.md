# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pykour is a lightweight ASGI web framework for Python 3.13+ with Next.js-style file-based routing. It features built-in schema validation, dependency injection, database support (SQLite/PostgreSQL/MySQL), and middleware.

## Development Commands

| Task | Command |
|------|---------|
| Run tests | `uv run pytest` |
| Run single test | `uv run pytest tests/test_router.py::test_function_name -v` |
| Lint | `uv run ruff check` |
| Lint (auto-fix) | `uv run ruff check --fix` |
| Format | `uv run ruff format` |
| Type check | `uv run ty check` |
| Run example app | `uv run pykour run examples.app:app --reload` |

**Workflow after code modification:**
1. `uv run ruff check --fix` - auto-fix lint issues
2. `uv run ruff format` - format code
3. Manually fix remaining lint issues
4. `uv run ty check` - type checking
5. `uv run pytest` - verify tests pass

## Architecture

### File-Based Routing

Routes are defined by file structure in a `routes/` directory:
- `routes/route.py` → `/`
- `routes/api/users/route.py` → `/api/users`
- `routes/api/users/[id]/route.py` → `/api/users/{id}` (dynamic segment)

Each `route.py` exports HTTP method handlers as async functions named `get`, `post`, `put`, `delete`, `patch`.

### Core Modules

- **`src/pykour/application.py`**: `Pykour` class - ASGI app with middleware stack, parameter injection, lifespan handling
- **`src/pykour/router.py`**: `Router` class - file-based route discovery and pattern matching
- **`src/pykour/request.py`**: `Request` class - ASGI scope wrapper with lazy body/JSON parsing
- **`src/pykour/response.py`**: `Response`, `JSONResponse` classes

### Parameter Injection

Handlers receive parameters via type hints and marker defaults:
- `Path()` - path parameters from URL segments
- `Query()` - query string parameters with validation
- `Body()` - JSON request body (supports `Schema`, dataclasses, pydantic)
- `Depends()` - dependency injection from service container

### Schema Validation (`src/pykour/schema/`)

Custom validation system (not pydantic):
- `Schema` base class for request body validation
- `Field()` for field constraints (ge, le, min_length, pattern, etc.)
- `field_validator`, `model_validator` decorators

### Database (`src/pykour/db/`)

- `Database` class with query builder API (`select`, `insert`, `update`, `delete`)
- Driver abstraction for SQLite, PostgreSQL, MySQL
- Access policies for row-level security
- Migration system (`src/pykour/db/migrations/`)

### Middleware (`src/pykour/middleware/`)

- `BaseMiddleware` for class-based middleware
- `@app.middleware` decorator for function-based middleware
- Built-in: CORS, JWT auth, rate limiting, security headers, logging, tracing

### Dependency Injection (`src/pykour/di/`)

- `ServiceContainer` for service registration
- `Depends()` marker for handler parameter injection
- Supports singletons, transient, and factory patterns

### Testing (`src/pykour/testing/`)

- `TestClient` for async ASGI testing without HTTP server
- `SyncTestClient` wrapper for synchronous tests

## Test Structure

Tests use pytest with pytest-asyncio (auto mode). Test files are in `tests/` with fixtures in `conftest.py`.

Routes for testing are in `tests/routes/` and follow the same file-based pattern.
