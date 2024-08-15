# Connection

Connection is a class that represents a connection to a database. Connections are used to communicate with databases.

## Creating a Connection

To create a connection, create a root function with the class `Connection` as an argument.

```python
from pykour import Pykour, Config
from pykour.db import Connection

app = Pykour(config=Config("config.yml"))

@app.get("/")
def index(conn: Connection):
    return conn.fetch_one("SELECT * FROM users")
```

The above example creates an `index` function with the `Connection` class as an argument.
This function uses the `Connection` class to retrieve user information from the database.

## Connection Methods

The `Connection` class provides a low-level API.

### `fetch_one` method

The `fetch_one` method executes the specified SQL query and returns the first row of results.

```python
result = conn.fetch_one("SELECT * FROM users")
```

### `fetch_all` method

The `fetch_all` method executes the given SQL query and returns all rows of the result.

```python
results = conn.fetch_all("SELECT * FROM users")
```

### `execute` method

The `execute` method executes the specified SQL query. The `execute` method returns the number of rows executed.

```python
ret = conn.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
```

### `commit` method

The `commit` method commits a transaction.

```python
conn.commit()
```

### `rollback` method

The `rollback` method rolls back a transaction.

```python
conn.rollback()
```

### `close` method

The `close` method closes a connection.

```python
conn.close()
```

## Parameterized Queries

Parameterization, rather than embedding variables directly in SQL, allows for separation of query and parameters.

```python
result = conn.fetch_one("SELECT * FROM users WHERE id = ?", 1)
```

The above example uses the `?` placeholder to specify the parameter.
The second argument to the `fetch_one` method is the parameter value.
