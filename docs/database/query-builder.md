# Query Builder

Pykour's query builder provides a fluent, chainable API for constructing SQL queries. All query methods return `self`, so you can chain calls together.

## SELECT

Create a SELECT query with `db.select()`:

```python
# Select specific columns
users = await db.select("id", "name", "email").from_("users").fetch_all()

# Select all columns
users = await db.select("*").from_("users").fetch_all()

# Fetch a single row
user = await db.select("*").from_("users").where(id=1).fetch_one()
```

| Method | SQL Equivalent | Description |
|:-------|:---------------|:------------|
| `select(*columns)` | `SELECT columns` | Specify columns to select |
| `.from_(table)` | `FROM table` | Set the table |
| `.distinct()` | `SELECT DISTINCT` | Enable DISTINCT |
| `.where(**conditions)` | `WHERE col = val AND ...` | Add equality conditions |
| `.order_by(*columns, desc=False)` | `ORDER BY col ASC/DESC` | Add ordering |
| `.limit(n)` | `LIMIT n` | Limit result count |
| `.offset(n)` | `OFFSET n` | Skip rows |
| `.join(table, on)` | `INNER JOIN table ON ...` | Inner join |
| `.left_join(table, on)` | `LEFT JOIN table ON ...` | Left join |
| `.group_by(*columns)` | `GROUP BY columns` | Group results |
| `.having(condition, *args)` | `HAVING condition` | Filter groups |
| `.fetch_all()` | - | Execute and return all rows (`list[Row]`) |
| `.fetch_one()` | - | Execute and return one row (`Row | None`) |

### DISTINCT

```python
cities = await db.select("city").from_("users").distinct().fetch_all()
# SELECT DISTINCT city FROM users
```

### ORDER BY

```python
# Ascending (default)
users = await db.select("*").from_("users").order_by("name").fetch_all()

# Descending
users = await db.select("*").from_("users").order_by("created_at", desc=True).fetch_all()

# Multiple columns
users = (
    await db.select("*").from_("users")
    .order_by("last_name")
    .order_by("first_name")
    .fetch_all()
)
```

### LIMIT / OFFSET (Pagination)

```python
# Get page 2 with 10 items per page
users = (
    await db.select("*").from_("users")
    .order_by("id")
    .limit(10)
    .offset(10)
    .fetch_all()
)
```

### JOIN

```python
# INNER JOIN
rows = (
    await db.select("users.name", "orders.total")
    .from_("users")
    .join("orders", "users.id = orders.user_id")
    .fetch_all()
)
# SELECT users.name, orders.total FROM users INNER JOIN orders ON users.id = orders.user_id

# LEFT JOIN
rows = (
    await db.select("users.name", "orders.total")
    .from_("users")
    .left_join("orders", "users.id = orders.user_id")
    .fetch_all()
)
```

### GROUP BY / HAVING

```python
stats = (
    await db.select("city", "COUNT(*) as count")
    .from_("users")
    .group_by("city")
    .having("COUNT(*) > $1", 5)
    .fetch_all()
)
# SELECT city, COUNT(*) as count FROM users GROUP BY city HAVING COUNT(*) > ?
```

## WHERE Conditions

All queries that support WHERE (SELECT, UPDATE, DELETE) share the same set of condition methods.

### Equality

```python
# Single condition
users = await db.select("*").from_("users").where(active=True).fetch_all()
# WHERE active = ?

# Multiple conditions (AND)
users = await db.select("*").from_("users").where(active=True, role="admin").fetch_all()
# WHERE active = ? AND role = ?
```

### Comparison Operators

```python
# Greater than
users = await db.select("*").from_("users").where_gt("age", 18).fetch_all()
# WHERE age > ?

# Greater than or equal
users = await db.select("*").from_("users").where_gte("age", 18).fetch_all()
# WHERE age >= ?

# Less than
users = await db.select("*").from_("users").where_lt("age", 65).fetch_all()
# WHERE age < ?

# Less than or equal
users = await db.select("*").from_("users").where_lte("age", 65).fetch_all()
# WHERE age <= ?
```

### IN / NOT IN

```python
# IN
users = await db.select("*").from_("users").where_in("role", ["admin", "editor"]).fetch_all()
# WHERE role IN (?, ?)

# NOT IN
users = await db.select("*").from_("users").where_not_in("status", ["banned", "deleted"]).fetch_all()
# WHERE status NOT IN (?, ?)
```

### BETWEEN

```python
users = await db.select("*").from_("users").where_between("age", 18, 65).fetch_all()
# WHERE age BETWEEN ? AND ?
```

### LIKE

```python
users = await db.select("*").from_("users").where_like("name", "A%").fetch_all()
# WHERE name LIKE ?
```

### NULL Checks

```python
# IS NULL
users = await db.select("*").from_("users").where_is_null("deleted_at").fetch_all()
# WHERE deleted_at IS NULL

# IS NOT NULL
users = await db.select("*").from_("users").where_is_not_null("email").fetch_all()
# WHERE email IS NOT NULL
```

### Raw WHERE

For complex conditions, use `where_raw()` with `$1`, `$2`, ... placeholders:

```python
users = (
    await db.select("*").from_("users")
    .where_raw("age > $1 AND (role = $2 OR role = $3)", 18, "admin", "editor")
    .fetch_all()
)
```

### Combining Conditions

All WHERE methods can be chained. They are combined with AND:

```python
users = (
    await db.select("*").from_("users")
    .where(active=True)
    .where_gt("age", 18)
    .where_like("name", "A%")
    .fetch_all()
)
# WHERE active = ? AND age > ? AND name LIKE ?
```

## INSERT

Create an INSERT query with `db.insert()`:

```python
# Insert a single row
await db.insert("users").values(name="Alice", email="alice@example.com").execute()

# Insert and get the result
row = await db.insert("users").values(name="Alice").returning("id").fetch_one()
new_id = row["id"]
```

| Method | Description |
|:-------|:------------|
| `insert(table)` | Start an INSERT query |
| `.values(**data)` | Set column-value pairs |
| `.values_many(rows)` | Insert multiple rows |
| `.returning(*columns)` | Add RETURNING clause |
| `.on_conflict_do_nothing(...)` | Handle conflicts by doing nothing |
| `.on_conflict_do_update(...)` | Handle conflicts by updating |
| `.execute()` | Execute and return affected row count (`int`) |
| `.fetch_one()` | Execute and return the inserted row (`Row | None`) |

### Bulk Insert

```python
await db.insert("users").values_many([
    {"name": "Alice", "email": "alice@example.com"},
    {"name": "Bob", "email": "bob@example.com"},
    {"name": "Carol", "email": "carol@example.com"},
]).execute()
```

### RETURNING

```python
row = (
    await db.insert("users")
    .values(name="Alice", email="alice@example.com")
    .returning("id", "created_at")
    .fetch_one()
)
print(row["id"], row["created_at"])
```

### ON CONFLICT (Upsert)

```python
# Do nothing on conflict
await (
    db.insert("users")
    .values(email="alice@example.com", name="Alice")
    .on_conflict_do_nothing("email")
    .execute()
)

# Update on conflict
await (
    db.insert("users")
    .values(email="alice@example.com", name="Alice Updated")
    .on_conflict_do_update("email", name="Alice Updated")
    .execute()
)

# Using a constraint name
await (
    db.insert("users")
    .values(email="alice@example.com", name="Alice")
    .on_conflict_do_nothing(constraint="uq_users_email")
    .execute()
)

# Conflict on multiple columns
await (
    db.insert("user_roles")
    .values(user_id=1, role_id=2)
    .on_conflict_do_nothing(["user_id", "role_id"])
    .execute()
)
```

## UPDATE

Create an UPDATE query with `db.update()`:

```python
# Update rows
count = await db.update("users").set(name="Bob").where(id=1).execute()

# Update with RETURNING
rows = (
    await db.update("users")
    .set(active=False)
    .where(role="guest")
    .returning("id", "name")
    .fetch_all()
)
```

| Method | Description |
|:-------|:------------|
| `update(table)` | Start an UPDATE query |
| `.set(**data)` | Set columns to update |
| `.where(...)` / `.where_*()` | Add WHERE conditions |
| `.returning(*columns)` | Add RETURNING clause |
| `.execute()` | Execute and return affected row count (`int`) |
| `.fetch_all()` | Execute and return updated rows (`list[Row]`) |

## DELETE

Create a DELETE query with `db.delete()`:

```python
# Delete rows
count = await db.delete("users").where(id=1).execute()

# Delete with RETURNING
deleted = (
    await db.delete("users")
    .where(active=False)
    .returning("id", "email")
    .fetch_all()
)
```

| Method | Description |
|:-------|:------------|
| `delete(table)` | Start a DELETE query |
| `.where(...)` / `.where_*()` | Add WHERE conditions |
| `.returning(*columns)` | Add RETURNING clause |
| `.execute()` | Execute and return affected row count (`int`) |
| `.fetch_all()` | Execute and return deleted rows (`list[Row]`) |

## Query Builder Summary

| Database Method | Returns | SQL |
|:----------------|:--------|:----|
| `db.select(*columns)` | `SelectQuery` | `SELECT` |
| `db.insert(table)` | `InsertQuery` | `INSERT` |
| `db.update(table)` | `UpdateQuery` | `UPDATE` |
| `db.delete(table)` | `DeleteQuery` | `DELETE` |
| `db.count(table, **cond)` | `int` | `SELECT COUNT(*)` |
| `db.exists(table, **cond)` | `bool` | `SELECT COUNT(*)` |
