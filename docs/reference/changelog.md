# Changelog

All notable changes to the Pykour framework are documented here. This project follows [Semantic Versioning](https://semver.org/).

## Version Format

Pykour uses **Semantic Versioning** (`MAJOR.MINOR.PATCH`):

- **MAJOR** -- Incompatible API changes
- **MINOR** -- New functionality in a backward-compatible manner
- **PATCH** -- Backward-compatible bug fixes

Pre-release versions use suffixes like `-rc1` (release candidate).

---

## v1.0.0-rc1 (Current)

The first release candidate of Pykour v1.0.0, featuring a complete rewrite as a modern async ASGI framework.

### Highlights

- Next.js-style **file-based routing** with dynamic segments
- Built-in **schema validation** system with field constraints and validators
- Full **dependency injection** container with singleton, transient, request-scoped, and async factory support
- **Database support** for SQLite, PostgreSQL, and MySQL with query builder and migration system
- Comprehensive **middleware stack** including CORS, JWT, rate limiting, and security headers
- **OpenAPI** auto-generation with security scheme support
- Async **test client** for ASGI testing without an HTTP server

### Features

- **OpenAPI Security Schemes** -- Auto-generation of security schemes from JWT middleware configuration (`2c6a8d1`)
- **Async Factory & REQUEST Scope** -- Dependency injection now supports async factory functions and per-request scoped services (`326dfa9`)
- **JWT Scopes & Auth Helpers** -- JWT authentication with scope-based authorization, schema error context, test client auth helpers, and transaction isolation levels (`48b24f6`)
- **File-Based Routing** -- Automatic route discovery from `routes/` directory structure with dynamic `[param]` segments
- **Schema Validation** -- `Schema` base class with `Field()` constraints (`ge`, `le`, `min_length`, `pattern`, etc.) and `field_validator`/`model_validator` decorators
- **Database Layer** -- Query builder API with `select`, `insert`, `update`, `delete` operations and driver abstraction
- **Migration System** -- Database migration support with squash capability (`c2b2192`)
- **Access Policies** -- Row-level security through database access policies
- **Middleware System** -- Class-based (`BaseMiddleware`) and decorator-based (`@app.middleware`) middleware support
- **WebSocket Support** -- WebSocket connection handling (`915605c`)
- **File Upload** -- File upload support with TUS protocol (`915605c`)
- **CLI Tool** -- `pykour` CLI for running applications, generating routes, and project scaffolding
- **Test Client** -- `TestClient` and `SyncTestClient` for testing without HTTP server

### Bug Fixes

- **SQLite/MySQL Column Operations** -- Fixed `AlterColumn` and `RenameColumn` operations for SQLite and MySQL drivers (`be7666d`)

### Refactoring

- **Query Builder & Middleware** -- Consolidated query builder, middleware, and type hints (`b9973b8`)
- **Database Type Safety** -- Improved type safety and reduced code duplication in the database layer (`c6a99e7`)
- **CLI & Access Policy** -- Added CLI configuration, access policy resolver, and removed database depends (`811dda0`)

---

## Pre-v1.0.0

Earlier development history includes migration from Poetry to uv and initial framework scaffolding. See the [Git history](https://github.com/pykour/pykour) for full details.

---
**See also:** [HTTP Exceptions](./exceptions.md) · [Getting Started](../getting-started/index.md)
[← Back to Home](../index.md)
