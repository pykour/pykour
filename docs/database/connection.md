# Connection

A connection is an object that represents a connection to a database.
You can use the connection to execute queries against the database.

## Creating a Connection

To create a connection, specify the `Connection` class as an argument in your route function.

```python
from pykour import Pykour
from pykour.db import Connection

app = Pykour("config.yml")

@app.get("/")
def index(conn: Connection):
    return conn.execute("SELECT * FROM users")
```

Connections are obtained from a connection pool managed by Pykour and are automatically returned to the pool when the request ends.

If the route function ends with a return statement, the transaction is committed. If an exception occurs, the transaction is rolled back.