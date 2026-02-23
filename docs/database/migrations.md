---
title: Migrations
parent: Database
nav_order: 3
---

# Migrations

Pykour includes a migration system for managing database schema changes. Migrations are Python files with `upgrade()` and `downgrade()` functions.

## Table Definitions

Define your schema using `Table` and `Column` classes:

```python
from pykour.db.migrations import Table, Column, Integer, String, Boolean, DateTime

class UserTable(Table):
    __tablename__ = "users"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    active = Column(Boolean(), default=True)
    created_at = Column(DateTime(), auto_now_add=True)
    updated_at = Column(DateTime(), auto_now=True)
```

### Column Types

| Type | Description | Parameters |
|:-----|:------------|:-----------|
| `Integer()` | Integer | `autoincrement` |
| `SmallInt()` | Small integer | - |
| `BigInt()` | Big integer | - |
| `String(length)` | Variable-length string | `length` (required) |
| `Text()` | Unlimited text | - |
| `Boolean()` | Boolean | - |
| `Float()` | Floating point | - |
| `Decimal(precision, scale)` | Exact decimal | `precision`, `scale` |
| `DateTime(timezone)` | Date and time | `timezone` (bool) |
| `Date()` | Date only | - |
| `Time()` | Time only | - |
| `Binary(length)` | Binary data | `length` (optional) |
| `JSON()` | JSON data | - |
| `UUID()` | UUID | - |

### Column Options

| Option | Type | Default | Description |
|:-------|:-----|:--------|:------------|
| `primary_key` | `bool` | `False` | Mark as primary key |
| `nullable` | `bool` | `True` | Allow NULL values |
| `unique` | `bool` | `False` | Add unique constraint |
| `default` | `Any` | `None` | Default value |
| `autoincrement` | `bool` | `False` | Auto-increment (primary key only) |
| `auto_now_add` | `bool` | `False` | Set to current UTC time on INSERT |
| `auto_now` | `bool` | `False` | Set to current UTC time on INSERT and UPDATE |
| `auto_set_on_insert` | `str` | `None` | Value to set on INSERT (e.g., `":user_id"`) |
| `auto_set` | `str` | `None` | Value to set on INSERT and UPDATE (e.g., `":tenant_id"`) |

Auto-set values use a `:` prefix to reference policy context keys:

- `":now"` -- Current UTC time
- `":user_id"` -- User ID from policy context
- `":tenant_id"` -- Tenant ID from policy context
- `":organization_id"` -- Organization ID from policy context
- `"literal"` -- A literal string value (no `:` prefix)

### Meta Class

Use the `Meta` inner class for indexes and constraints:

```python
class OrderTable(Table):
    __tablename__ = "orders"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), nullable=False)
    email = Column(String(255), nullable=False)
    domain = Column(String(100), nullable=False)
    created_at = Column(DateTime(), auto_now_add=True)
    updated_at = Column(DateTime(), auto_now=True)

    class Meta:
        # Composite unique constraints (creates UNIQUE INDEX)
        unique_together = [
            ("email", "domain"),
            ("tenant_id", "email"),
        ]

        # Search keys (creates INDEX)
        search_keys = [
            ["tenant_id"],
            ["email", "created_at"],
        ]
```

## Migration Files

Migration files are Python scripts in a `migrations/` directory with a versioned naming pattern: `0001_description.py`.

### Structure

```python
"""Create users table."""

from pykour.db.migrations import op


def upgrade():
    op.create_table(
        "users",
        op.column("id", "INTEGER", primary_key=True, autoincrement=True),
        op.column("name", "VARCHAR(100)", nullable=False),
        op.column("email", "VARCHAR(255)", unique=True, nullable=False),
        op.column("active", "BOOLEAN", default=True),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)


def downgrade():
    op.drop_index("idx_users_email")
    op.drop_table("users")
```

### Operation API (`op`)

#### Table Operations

```python
# Create a table
op.create_table(
    "users",
    op.column("id", "INTEGER", primary_key=True, autoincrement=True),
    op.column("name", "VARCHAR(100)", nullable=False),
    if_not_exists=False,  # Optional
)

# Drop a table
op.drop_table("users", if_exists=False)

# Rename a table
op.rename_table("old_name", "new_name")
```

#### Column Operations

```python
# Define a column (used in create_table)
op.column(
    "name",
    "VARCHAR(100)",
    primary_key=False,
    nullable=True,
    unique=False,
    default=None,
    autoincrement=False,
)

# Add a column
op.add_column("users", op.column("age", "INTEGER", nullable=True))

# Drop a column
op.drop_column("users", "age")

# Alter a column (type, nullable, default)
op.alter_column(
    "users",
    "name",
    new_type="VARCHAR(200)",
    nullable=False,
    new_default="Unknown",
)

# Drop default value
op.alter_column("users", "name", drop_default=True)

# Rename a column
op.rename_column("users", "old_name", "new_name")
```

{: .note }
`alter_column` and `rename_column` are supported on all three databases (SQLite, PostgreSQL, MySQL), with driver-specific SQL generation.

#### Index Operations

```python
# Create an index
op.create_index("idx_users_email", "users", ["email"])

# Create a unique index
op.create_index("idx_users_email", "users", ["email"], unique=True)

# Create a partial index (SQLite/PostgreSQL only)
op.create_index(
    "idx_active_users",
    "users",
    ["email"],
    where="active = 1",
)

# Drop an index
op.drop_index("idx_users_email")
```

#### Raw SQL

```python
op.execute(
    "CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1",
    reverse_sql="DROP VIEW active_users",
)
```

### Column Presets

Built-in presets for common column patterns:

```python
from pykour.db.migrations import op
from pykour.db.migrations.presets import timestamps, soft_delete, audit, created, updated

def upgrade():
    op.create_table(
        "users",
        op.column("id", "INTEGER", primary_key=True, autoincrement=True),
        timestamps,    # created_at TIMESTAMP + updated_at TIMESTAMP
        op.column("name", "VARCHAR(100)", nullable=False),
        soft_delete,   # is_deleted BOOLEAN DEFAULT FALSE
    )
```

| Preset | Columns |
|:-------|:--------|
| `timestamps` | `created_at` (TIMESTAMP, NOT NULL, DEFAULT CURRENT_TIMESTAMP), `updated_at` (TIMESTAMP) |
| `created` | `created_at` (TIMESTAMP, NOT NULL, DEFAULT CURRENT_TIMESTAMP), `created_by` (VARCHAR(100)) |
| `updated` | `updated_at` (TIMESTAMP), `updated_by` (VARCHAR(100)) |
| `audit` | `created_at`, `created_by`, `updated_at`, `updated_by` |
| `soft_delete` | `is_deleted` (BOOLEAN, NOT NULL, DEFAULT FALSE) |

Define custom presets:

```python
from pykour.db.migrations.presets import ColumnGroup
from pykour.db.migrations.table import ColumnDef

tenant_columns = ColumnGroup("tenant", [
    ColumnDef("tenant_id", "VARCHAR(36)", nullable=False),
    ColumnDef("organization_id", "VARCHAR(36)", nullable=True),
])

# Use in create_table
op.create_table(
    "orders",
    op.column("id", "INTEGER", primary_key=True),
    tenant_columns,  # Expands to tenant_id + organization_id
)
```

## CLI Commands

Manage migrations using the `pykour migrate` CLI:

### Initialize

```bash
# Create migrations directory
pykour migrate init

# Create directory and migrations table in database
pykour migrate init --database
```

### Create a Migration

```bash
# Empty migration
pykour migrate new -m "add user roles"

# Auto-generate from schema diff
pykour migrate generate --models app.models -m "create initial tables"
```

The `generate` command compares your `Table` definitions against the current database schema and generates the necessary operations.

### Apply Migrations

```bash
# Apply all pending migrations
pykour migrate up

# Apply N migrations
pykour migrate up --steps 1
```

### Rollback Migrations

```bash
# Rollback the last migration
pykour migrate down

# Rollback N migrations
pykour migrate down --steps 3
```

### Check Status

```bash
# View migration status
pykour migrate status

# View migration history
pykour migrate history
```

## Programmatic Usage

Use `MigrationRunner` directly for programmatic control:

```python
from pathlib import Path
from pykour.db import Database
from pykour.db.migrations import MigrationRunner

db = Database("sqlite:///app.db")
await db.connect()

runner = MigrationRunner(db, Path("migrations"))
await runner.init()

# Apply all pending migrations
applied = await runner.up()

# Rollback last migration
rolled_back = await runner.down(steps=1)

# Check status
status = await runner.status()
print(status["pending_count"])

# Get history
history = await runner.history()

await db.disconnect()
```

---

{: .fs-2 .text-muted }
Pykour Documentation
