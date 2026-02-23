# CRUD Generation

Pykour can automatically generate CRUD (Create, Read, Update, Delete) endpoints for your database tables, either at runtime via `register_crud()` or at development time via the CLI.

## Runtime Registration with `register_crud()`

The `register_crud()` method on the `Pykour` application creates REST endpoints for a `Table` class:

```python
from pykour import Pykour
from pykour.db.migrations import Table, Column, Integer, String

class UserTable(Table):
    __tablename__ = "users"
    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)

app = Pykour(routes_dir="routes", database=db)
app.register_crud("/api/users", UserTable)
```

### Generated Endpoints

By default, all five CRUD operations are registered:

| Method | Path | Operation | Description |
|--------|------|-----------|-------------|
| `GET` | `/api/users` | `list` | List records with pagination. |
| `GET` | `/api/users/{id}` | `get` | Get a single record by ID. |
| `POST` | `/api/users` | `create` | Create a new record. |
| `PUT` | `/api/users/{id}` | `update` | Update an existing record. |
| `DELETE` | `/api/users/{id}` | `delete` | Delete a record. |

### Parameters

```python
app.register_crud(
    path: str,
    table: type,
    *,
    operations: list[str] | None = None,
    list_config: ListConfig | None = None,
    id_field: str | None = None,
    exclude_fields: list[str] | None = None,
    readonly_fields: list[str] | None = None,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `path` | `str` | -- | Base path for endpoints (e.g., `"/api/users"`). |
| `table` | `type` | -- | Table class to generate CRUD for. |
| `operations` | `list[str]` | All | Operations to enable: `"list"`, `"get"`, `"create"`, `"update"`, `"delete"`. |
| `list_config` | `ListConfig` | Defaults | Configuration for the list endpoint. |
| `id_field` | `str` | Auto-detected | Primary key field name. |
| `exclude_fields` | `list[str]` | `[]` | Fields to exclude from the API. |
| `readonly_fields` | `list[str]` | `[]` | Fields that cannot be set on create/update. |

### Selecting Operations

```python
# Read-only API
app.register_crud("/api/users", UserTable, operations=["list", "get"])

# No delete
app.register_crud(
    "/api/users", UserTable,
    operations=["list", "get", "create", "update"],
)
```

### ListConfig

Configure the list endpoint behavior:

```python
from pykour.crud.config import ListConfig

app.register_crud(
    "/api/users",
    UserTable,
    list_config=ListConfig(
        default_limit=20,
        max_limit=100,
        sortable_fields=["name", "email", "created_at"],
        filterable_fields=["name", "email"],
    ),
)
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_limit` | `int` | `20` | Default page size. |
| `max_limit` | `int` | `100` | Maximum allowed page size. |
| `sortable_fields` | `list[str] \| None` | `None` | Fields allowed for sorting. `None` allows all. |
| `filterable_fields` | `list[str] \| None` | `None` | Fields allowed for filtering. `None` allows all. |

### Excluding and Readonly Fields

```python
app.register_crud(
    "/api/users",
    UserTable,
    exclude_fields=["password_hash"],       # Never exposed in API
    readonly_fields=["id", "created_at"],   # Cannot be set by client
)
```

## CLI Code Generation

The `pykour generate crud` command creates route files on disk that you can customize:

```bash
# Basic CRUD generation
pykour generate crud users

# With validation schema and tests
pykour generate crud products --with-schema --with-tests

# With table class for field inference
pykour generate crud users --table-class models.tables:UserTable

# Custom options
pykour generate crud orders --table orders --id-type str --id-field order_id
```

See the [CLI page](cli#pykour-generate-crud) for all options.

## CRUDConfig

The internal configuration dataclass used by `register_crud()`:

```python
@dataclass
class CRUDConfig:
    path: str
    table: type[Table]
    operations: list[str] = ["list", "get", "create", "update", "delete"]
    list_config: ListConfig = ListConfig()
    id_field: str | None = None
    exclude_fields: list[str] = []
    readonly_fields: list[str] = []
```
