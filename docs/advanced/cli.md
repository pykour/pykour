---
title: CLI
parent: Advanced
nav_order: 5
---

# CLI
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

Pykour includes a command-line interface for running the development server, inspecting routes, generating scaffolding code, and managing database migrations.

## `pykour run`

Start the development server (powered by uvicorn).

```
pykour run APP [OPTIONS]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `APP` | Application module path (e.g., `app:app` or `main:application`). If the app name is omitted, defaults to `app`. |

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--host HOST` | `127.0.0.1` | Host to bind. |
| `--port PORT` | `8000` | Port to bind. |
| `--reload` | -- | Enable auto-reload on code changes. |
| `--reload-dir PATH` | -- | Directories to watch (repeatable). |
| `--reload-include PATTERN` | -- | Glob patterns to include for watching (repeatable). |
| `--reload-exclude PATTERN` | -- | Glob patterns to exclude (repeatable). |
| `--workers N` | `1` | Number of worker processes. Mutually exclusive with `--reload`. |
| `--log-format {text,json}` | `text` | Log output format. |
| `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}` | `INFO` | Log level. |
| `--debug` | -- | Enable debug mode (auto-enables reload, sets DEBUG log level). |
| `--auto-migrate` | -- | Run pending migrations before starting the server. |
| `--migrations-dir DIR` | `migrations` | Migrations directory. |
| `--database URL` | -- | Database URL for migrations (defaults to `PYKOUR_DATABASE_URL`). |

### Examples

```bash
# Basic usage
pykour run app:app

# Development with auto-reload
pykour run app:app --reload

# Debug mode (reload + DEBUG logs)
pykour run app:app --debug

# Production-like with multiple workers
pykour run app:app --host 0.0.0.0 --port 80 --workers 4

# With auto-migration
pykour run app:app --reload --auto-migrate --database sqlite:///app.db
```

## `pykour routes`

Display registered routes from the routes directory.

```
pykour routes [OPTIONS]
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--routes-dir DIR` | `routes` | Routes directory path. |
| `--verbose, -v` | -- | Show detailed route information (parameters, catch-all). |

### Examples

```bash
# List all routes
pykour routes

# Verbose output
pykour routes -v

# Custom routes directory
pykour routes --routes-dir src/routes
```

## `pykour generate`

Generate scaffolding code. Aliases: `gen`, `g`.

### `pykour generate route`

Generate a route file with specified HTTP method handlers.

```
pykour generate route METHOD PATH [OPTIONS]
```

| Argument | Description |
|----------|-------------|
| `METHOD` | HTTP method(s): `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `CRUD`, or comma-separated (e.g., `GET,POST`). |
| `PATH` | URL path (e.g., `/api/v1/hello`, `/api/users/{id}`). |

| Option | Default | Description |
|--------|---------|-------------|
| `--routes-dir DIR` | `routes` | Routes directory. |
| `--force, -f` | -- | Overwrite existing files. |

```bash
# Generate a GET endpoint
pykour generate route GET /api/users

# Generate CRUD endpoints
pykour generate route CRUD /api/products

# Generate multiple methods
pykour generate route GET,POST /api/items
```

### `pykour generate crud`

Generate complete CRUD endpoints for a resource, including optional schema and test files.

```
pykour generate crud RESOURCE [OPTIONS]
```

| Argument | Description |
|----------|-------------|
| `RESOURCE` | Resource name (e.g., `users`, `products`). |

| Option | Default | Description |
|--------|---------|-------------|
| `--table TABLE` | Resource name | Database table name. |
| `--id-field FIELD` | `id` | Primary key field name. |
| `--id-type {int,str}` | `int` | Primary key type. |
| `--routes-dir DIR` | `routes` | Routes directory. |
| `--with-schema` | -- | Generate schema file for validation. |
| `--with-tests` | -- | Generate test file. |
| `--force, -f` | -- | Overwrite existing files. |
| `--table-class PATH` | -- | Table class for field inference (e.g., `app.tables:UserTable`). |

```bash
# Basic CRUD
pykour generate crud users

# With schema and tests
pykour generate crud products --with-schema --with-tests

# With table class inference
pykour generate crud users --table-class models.tables:UserTable
```

## `pykour migrate`

Database migration management commands.

### Common Options

All migrate subcommands accept:

| Option | Default | Description |
|--------|---------|-------------|
| `--migrations-dir DIR` | `migrations` | Migrations directory. |
| `--database URL` | -- | Database URL (defaults to `PYKOUR_DATABASE_URL`). |

### `pykour migrate init`

Initialize the migrations directory and optionally create the migrations table in the database.

```bash
# Create directory only
pykour migrate init

# Create directory and database table
pykour migrate init --database sqlite:///app.db
```

### `pykour migrate new`

Create a new empty migration file.

```bash
pykour migrate new -m "add users table"
```

### `pykour migrate generate`

Generate a migration from schema diff by comparing Table definitions to the database.

```bash
pykour migrate generate -m "add email column" --database sqlite:///app.db
pykour migrate generate -m "initial" --models app.models --database sqlite:///app.db
```

| Option | Default | Description |
|--------|---------|-------------|
| `-m, --message` | -- | Migration message (required). |
| `--models MODULE` | `models` | Models module path. |

### `pykour migrate up`

Apply pending migrations.

```bash
# Apply all pending
pykour migrate up --database sqlite:///app.db

# Apply specific number
pykour migrate up 2 --database sqlite:///app.db
```

### `pykour migrate down`

Rollback applied migrations.

```bash
# Rollback last migration
pykour migrate down --database sqlite:///app.db

# Rollback specific number
pykour migrate down 3 --database sqlite:///app.db
```

### `pykour migrate status`

Show current migration status.

```bash
pykour migrate status --database sqlite:///app.db
```

Output includes: current version, total migrations, applied count, pending count, and list of pending migrations.

### `pykour migrate history`

Show migration history with applied timestamps.

```bash
pykour migrate history --database sqlite:///app.db
```

### `pykour migrate squash`

Squash multiple migrations into one.

```bash
# Squash all migrations
pykour migrate squash --all -m "initial" --database sqlite:///app.db

# Squash a range
pykour migrate squash --from 001 --to 005 -m "consolidate" --database sqlite:///app.db

# Dry run
pykour migrate squash --all -m "initial" --dry-run --database sqlite:///app.db
```

| Option | Description |
|--------|-------------|
| `--from, -f VERSION` | Start version (inclusive). |
| `--to, -t VERSION` | End version (inclusive). |
| `--all` | Squash all migrations. |
| `-m, --message` | Squashed migration message (required). |
| `--optimize` | Optimize operations (merge redundant ops). |
| `--dry-run` | Show what would be squashed without changes. |
| `-y, --yes` | Skip confirmation prompt. |

### `pykour migrate archive`

Archive (freeze) migrations to prevent rollback or squash.

```bash
# Archive up to a specific version
pykour migrate archive --to 005 --database sqlite:///app.db

# Dry run
pykour migrate archive --to 005 --dry-run --database sqlite:///app.db
```

---

{: .fs-2 .text-muted }
Pykour Documentation
