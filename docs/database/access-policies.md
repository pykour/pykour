---
title: Access Policies
parent: Database
nav_order: 4
---

# Access Policies

Access policies provide row-level security (RLS) for your database queries. They automatically add WHERE conditions and inject values into INSERT operations based on the current request context.

## Overview

An access policy defines:

- **Conditions** per operation (SELECT, INSERT, UPDATE, DELETE) that are automatically added to queries
- **Auto-set values** that are injected into INSERT operations
- **Bypass roles** that skip enforcement

This is useful for multi-tenant applications where each tenant should only see their own data.

## Defining Policies

### On a Table Definition

The recommended approach is to define policies directly on `Table` classes using the `Meta` class:

```python
from pykour.db.migrations import Table, Column, Integer, String, DateTime
from pykour.db.access_policy import AccessPolicy

class OrderTable(Table):
    __tablename__ = "orders"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    total = Column(Integer(), nullable=False)
    created_at = Column(DateTime(), auto_now_add=True)

    class Meta:
        access_policy = AccessPolicy(
            name="orders_tenant_policy",
            select=["tenant_id = :tenant_id"],
            insert=["tenant_id = :tenant_id"],
            update=["tenant_id = :tenant_id", "user_id = :user_id"],
            delete=["tenant_id = :tenant_id", "user_id = :user_id"],
            auto_set={"tenant_id": ":tenant_id"},
            bypass_roles=["admin"],
        )
```

### Registering Standalone Policies

You can also register policies directly on the `Database` instance:

```python
from pykour.db.access_policy import AccessPolicy

policy = AccessPolicy(
    name="orders_tenant_policy",
    select=["tenant_id = :tenant_id"],
    insert=["tenant_id = :tenant_id"],
    auto_set={"tenant_id": ":tenant_id"},
    bypass_roles=["admin"],
)

db.register_policy("orders", policy)
```

## AccessPolicy Parameters

| Parameter | Type | Description |
|:----------|:-----|:------------|
| `name` | `str` | Policy name (for debugging and migrations) |
| `select` | `list[str]` | Conditions added to SELECT queries |
| `insert` | `list[str]` | Conditions validated on INSERT |
| `update` | `list[str]` | Conditions added to UPDATE queries |
| `delete` | `list[str]` | Conditions added to DELETE queries |
| `auto_set` | `dict[str, str]` | Columns auto-set on INSERT (column -> context key) |
| `bypass_roles` | `list[str]` | Roles that bypass enforcement |

Condition strings use `:key` syntax to reference context values:

- `"tenant_id = :tenant_id"` -- Adds `WHERE tenant_id = <context.tenant_id>`
- `"user_id = :user_id"` -- Adds `WHERE user_id = <context.user_id>`

## Setting the Policy Context

The policy context stores the current user's tenant, user ID, roles, etc. It must be set for each request.

### Using the Middleware

The `AccessPolicyMiddleware` automatically extracts context from requests:

```python
from pykour import Pykour
from pykour.db import Database
from pykour.db.access_policy import AccessPolicyMiddleware

db = Database("postgresql://localhost/myapp")
app = Pykour(database=db)

app = AccessPolicyMiddleware(
    app,
    tenant_extractor=lambda req: req.headers.get("x-tenant-id"),
    user_extractor=lambda req: getattr(req.state, "user_id", None),
    organization_extractor=lambda req: getattr(req.state, "org_id", None),
    roles_extractor=lambda req: getattr(req.state, "roles", []),
    custom_extractors={
        "region": lambda req: req.headers.get("x-region"),
    },
)
```

Extractors can be sync or async functions:

```python
async def get_tenant(req):
    # Async extraction
    return req.headers.get("x-tenant-id")

app = AccessPolicyMiddleware(
    app,
    tenant_extractor=get_tenant,
)
```

### Helper Functions

Use built-in helpers for common extraction patterns:

```python
from pykour.db.access_policy import (
    AccessPolicyMiddleware,
    create_header_extractor,
    create_state_extractor,
)

app = AccessPolicyMiddleware(
    app,
    tenant_extractor=create_header_extractor("X-Tenant-ID"),
    user_extractor=create_state_extractor("user_id"),
    roles_extractor=create_state_extractor("roles"),
)
```

### Manual Context

Set the context manually using `set_policy_context()`:

```python
from pykour.db.access_policy import set_policy_context

set_policy_context(
    tenant_id="t-123",
    user_id="u-456",
    roles=["admin"],
)

# All subsequent queries will apply policies with this context
orders = await db.select("*").from_("orders").fetch_all()
```

### Context Manager

Use `PolicyContextManager` for scoped context:

```python
from pykour.db.access_policy import PolicyContextManager

# Sync context manager
with PolicyContextManager(tenant_id="t-123", user_id="u-456"):
    orders = await db.select("*").from_("orders").fetch_all()
# Context is automatically cleared

# Async context manager
async with PolicyContextManager(tenant_id="t-123"):
    orders = await db.select("*").from_("orders").fetch_all()
```

### Bypassing Enforcement

For admin operations that need to skip policy enforcement:

```python
set_policy_context(bypass_enforcement=True)

# This query runs without policy conditions
all_orders = await db.select("*").from_("orders").fetch_all()
```

Or via `PolicyContextManager`:

```python
with PolicyContextManager(bypass_enforcement=True):
    all_orders = await db.select("*").from_("orders").fetch_all()
```

## PolicyContextData

The `PolicyContextData` stores the context for the current request:

| Attribute | Type | Description |
|:----------|:-----|:------------|
| `tenant_id` | `Any` | Tenant identifier |
| `user_id` | `Any` | User identifier |
| `organization_id` | `Any` | Organization identifier |
| `roles` | `list[str]` | User roles |
| `custom` | `dict[str, Any]` | Custom context values |
| `bypass_enforcement` | `bool` | Skip policy enforcement |

## How It Works

When a query is executed with policies enabled:

1. **SELECT**: Policy conditions are appended to the WHERE clause
   ```sql
   -- Before policy
   SELECT * FROM orders
   -- After policy (tenant_id = :tenant_id)
   SELECT * FROM orders WHERE tenant_id = 't-123'
   ```

2. **INSERT**: Auto-set values are injected, and insert conditions are validated
   ```python
   # User writes:
   await db.insert("orders").values(total=100).execute()
   # With auto_set={"tenant_id": ":tenant_id"}, the query becomes:
   # INSERT INTO orders (total, tenant_id) VALUES (100, 't-123')
   ```

3. **UPDATE**: Policy conditions are appended to the WHERE clause
   ```sql
   -- Before policy
   UPDATE orders SET total = 200 WHERE id = 1
   -- After policy
   UPDATE orders SET total = 200 WHERE id = 1 AND tenant_id = 't-123'
   ```

4. **DELETE**: Policy conditions are appended to the WHERE clause
   ```sql
   -- Before policy
   DELETE FROM orders WHERE id = 1
   -- After policy
   DELETE FROM orders WHERE id = 1 AND tenant_id = 't-123'
   ```

## Bypass Roles

If the current user has a role in `bypass_roles`, policy conditions are skipped:

```python
AccessPolicy(
    select=["tenant_id = :tenant_id"],
    bypass_roles=["admin", "superadmin"],
)

# Admin user bypasses the policy
set_policy_context(tenant_id="t-123", roles=["admin"])
all_orders = await db.select("*").from_("orders").fetch_all()
# SELECT * FROM orders (no tenant_id filter)
```

## Migration Operations

Manage access policies in migration files:

```python
from pykour.db.migrations import op

def upgrade():
    op.create_access_policy(
        "orders",
        "orders_tenant_policy",
        select=["tenant_id = :tenant_id"],
        insert=["tenant_id = :tenant_id"],
        auto_set={"tenant_id": ":tenant_id"},
        bypass_roles=["admin"],
    )

def downgrade():
    op.drop_access_policy("orders", "orders_tenant_policy")
```

Alter an existing policy:

```python
def upgrade():
    op.alter_access_policy(
        "orders",
        "orders_tenant_policy",
        new_select=["tenant_id = :tenant_id", "active = true"],
    )
```

---

{: .fs-2 .text-muted }
Pykour Documentation
