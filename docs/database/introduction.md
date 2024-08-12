# Database

Pykour provides facilities for connecting to and working with databases.

## Database connection

To connect to a database, specify the connection information in the configuration file.

```yaml
pykour:
    datasource:
        type: sqlite
        db: /path/to/database.sqlite
```

```python
from pykour import Pykour, Config

app = Pykour(config=Config("config.yml"))

@app.get("/")
def index():
    return {"message": "Hello, World!"}
```

This example connects to a SQLite database called `database.sqlite` located at `/path/to`.

### Connecting to Sqlite

To connect to a Sqlite database, specify `pykour.datasource.type` as `sqlite`.

```yaml
pykour:
    datasource:
        type: sqlite
        db: /path/to/database.sqlite
```

If you want to use an in-memory database, specify `file::memory:` for `db`.

```yaml
pykour:
    datasource:
        type: sqlite
        db: file::memory:?cache=shared
```

### Connecting to MySQL

To connect to a MySQL database, specify `mysql` in `pykour.datasource.type`.

```yaml
pykour:
    datasource:
        type: mysql
        host: localhost
        db: dbname
        username: user
        password: password
```

### Connecting to MariaDB

To connect to a MariaDB database, specify `mariadb` for `pykour.datasource.type`.

```yaml
pykour:
    datasource:
        type: maria
        host: localhost
        db: dbname
        username: user
        password: password
```

###  Connecting to PostgreSQL

To connect to a PostgreSQL database, specify `postgres` in `pykour.datasource.type`.

```yaml
pykour:
    datasource:
        type: postgres
        host: localhost
        db: dbname
        username: user
        password: password
```

## Connection Pool

Pykour uses connection pools to manage database connections.
Connection pools allow for reuse of connections to improve application performance.
Connection pool pools 5 connections by default, but you can change the number of connections using 
`pykour.datasource.pool.max_connections`.

```yaml
pykour:
    datasource:
        type: sqlite
        db: /path/to/database.sqlite
        pool:
            max_connections: 10
```

Use the `Connection` class to connect to and manipulate the database, which uses a connection pool to manage connections.
