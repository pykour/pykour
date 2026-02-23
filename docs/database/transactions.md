---
title: Transactions
parent: Database
nav_order: 2
---

# Transactions

Pykour provides transaction support with automatic commit/rollback, isolation levels, and savepoints.

## Basic Usage

Use `db.transaction()` as an async context manager. The transaction commits automatically on success and rolls back on exception:

```python
async with await db.transaction():
    await db.insert("users").values(name="Alice").execute()
    await db.insert("accounts").values(user_id=1, balance=100).execute()
    # Commits automatically when the block exits without error

# If an exception occurs, the transaction is rolled back automatically
```

{: .important }
Note the `await` before `db.transaction()`. The method is async and returns a `Transaction` context manager.

## Explicit Commit and Rollback

You can commit or rollback manually within the transaction:

```python
async with await db.transaction() as tx:
    await db.insert("users").values(name="Alice").execute()

    if some_condition:
        await tx.commit()    # Explicit commit
    else:
        await tx.rollback()  # Explicit rollback
```

If you call `commit()` or `rollback()` explicitly, the context manager will not perform an automatic commit/rollback on exit.

## Isolation Levels

Specify a transaction isolation level:

```python
async with await db.transaction(isolation="SERIALIZABLE"):
    await db.insert("users").values(name="Alice").execute()
```

Supported isolation levels:

| Level | Description |
|:------|:------------|
| `"READ UNCOMMITTED"` | Allows dirty reads |
| `"READ COMMITTED"` | Only reads committed data |
| `"REPEATABLE READ"` | Consistent reads within the transaction |
| `"SERIALIZABLE"` | Full serialization of transactions |

The `IsolationLevel` type is a `Literal` type alias:

```python
from pykour.db import IsolationLevel

level: IsolationLevel = "SERIALIZABLE"
```

{: .note }
Not all databases support all isolation levels. SQLite defaults to `SERIALIZABLE`. Check your database documentation for details.

## Savepoints

Savepoints allow partial rollbacks within a transaction:

```python
async with await db.transaction() as tx:
    await db.insert("users").values(name="Alice").execute()

    # Create a savepoint
    await tx.savepoint("before_update")

    try:
        await db.update("users").set(status="active").execute()
    except Exception:
        # Rollback to savepoint (the INSERT is preserved)
        await tx.rollback_to("before_update")

    # Optionally release a savepoint (auto-released on commit)
    await tx.release_savepoint("before_update")
```

### Savepoint API

| Method | Description |
|:-------|:------------|
| `await tx.savepoint(name)` | Create a named savepoint |
| `await tx.rollback_to(name)` | Rollback to a savepoint (transaction stays active) |
| `await tx.release_savepoint(name)` | Release a savepoint (optional, auto-released on commit) |

## Error Handling

```python
from pykour.db import DatabaseConnectionException

try:
    async with await db.transaction():
        await db.insert("users").values(name="Alice").execute()
        raise ValueError("Something went wrong")
except ValueError:
    # Transaction was automatically rolled back
    pass
```

Calling `commit()` after a rollback, or `rollback()` after a commit, raises `RuntimeError`:

```python
async with await db.transaction() as tx:
    await tx.rollback()
    await tx.commit()  # RuntimeError: Cannot commit: transaction already rolled back
```

## Accessing the Connection

If you need the underlying database connection for advanced operations:

```python
async with await db.transaction() as tx:
    conn = tx.connection
    # Use conn for driver-specific operations
```

## Transaction Scope

All query builder operations within a transaction block automatically use the transaction's connection:

```python
async with await db.transaction():
    # Both operations use the same connection and transaction
    await db.insert("orders").values(user_id=1, total=50).execute()
    count = await db.select("COUNT(*) as c").from_("orders").where(user_id=1).fetch_one()
```

---

{: .fs-2 .text-muted }
Pykour Documentation
