# Database

Pykour provides functionality for using a database.

## Connecting to the Database

To connect to a database, you need to specify the connection information in the configuration file.

```yaml
pykour:
    database:
        type: sqlite
        url: /path/to/database.sqlite
```

The example above shows the configuration for connecting to an SQLite database.
