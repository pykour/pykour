# Database

Pykour provides built-in database support with a fluent query builder, connection pooling, transactions, migrations, and row-level access policies.

## Supported Databases

| Database   | Driver Package | Connection URL Format |
|:-----------|:---------------|:----------------------|
| SQLite     | `aiosqlite`    | `sqlite:///path/to/db.sqlite` or `sqlite:///:memory:` |
| PostgreSQL | `asyncpg`      | `postgresql://user:pass@host:port/dbname` |
| MySQL      | `aiomysql`     | `mysql://user:pass@host:port/dbname` |

## Setup

### Installation

Install the driver for your database:

```bash
# SQLite (included with Python)
pip install aiosqlite

# PostgreSQL
pip install asyncpg

# MySQL
pip install aiomysql
```

### Configuration

The `Database` class accepts a connection URL directly, or reads it from environment variables / config file:

```python
from pykour.db import Database

# Direct URL
db = Database("sqlite:///app.db")

# From environment variable PYKOUR_DATABASE_URL
db = Database()

# From pykour.toml (database.url)
db = Database()
```

URL resolution order:

1. `url` argument passed to `Database()`
2. `PYKOUR_DATABASE_URL` environment variable
3. `database.url` in `pykour.toml`

### Connection Pool

Configure the connection pool size:

```python
db = Database(
    "postgresql://localhost/myapp",
    min_size=2,   # Minimum connections (default: 1)
    max_size=20,  # Maximum connections (default: 10)
)
```

### Connecting and Disconnecting

```python
await db.connect()

# ... use the database ...

await db.disconnect()
```

With a Pykour application, the database connects and disconnects automatically during the app lifespan:

```python
from pykour import Pykour
from pykour.db import Database

db = Database("sqlite:///app.db")
app = Pykour(database=db)
```

## Basic Usage

### Raw SQL

Execute raw SQL with parameterized queries using `$1`, `$2`, ... placeholders:

```python
# Execute (returns affected row count)
count = await db.execute(
    "INSERT INTO users (name, email) VALUES ($1, $2)",
    "Alice", "alice@example.com"
)

# Fetch all rows
rows = await db.fetch_all("SELECT * FROM users WHERE active = $1", True)

# Fetch one row
row = await db.fetch_one("SELECT * FROM users WHERE id = $1", 1)

# Fetch a single value
count = await db.fetch_val("SELECT COUNT(*) FROM users")
```

Placeholders are automatically converted to the appropriate format for each database driver (`?` for SQLite, `$1` for PostgreSQL, `%s` for MySQL).

### Query Builder

Pykour provides a fluent query builder for type-safe query construction:

```python
# SELECT
users = await db.select("id", "name").from_("users").where(active=True).fetch_all()

# INSERT
await db.insert("users").values(name="Alice", email="alice@example.com").execute()

# UPDATE
await db.update("users").set(name="Bob").where(id=1).execute()

# DELETE
await db.delete("users").where(id=1).execute()
```

See [Query Builder](query-builder.md) for the full API.

### Convenience Methods

```python
# Count rows
total = await db.count("users")
active = await db.count("users", active=True)

# Check existence
has_admin = await db.exists("users", role="admin")
```

### Auto-Discovering Table Models

Register table model modules to enable automatic access policy enforcement and column auto-set:

```python
db = Database(
    "postgresql://localhost/myapp",
    models="app.models",  # Single module
)

# Or multiple modules
db = Database(
    "postgresql://localhost/myapp",
    models=["app.models", "app.core.models"],
)
```

You can also register tables manually:

```python
db.register_table(UserTable)
db.register_tables([UserTable, OrderTable])
```
