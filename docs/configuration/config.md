# Config

The Config class holds the contents of the configuration file.

## Using in route handler

You can retrieve the contents of the configuration file by receiving `config` as an argument in your route handler.

```python
from pykour import Pykour, Config

app = Pykour('config.yaml')

@app.get('/')
def index(config: Config):
    return { 'message': config.get('message') }
```

## Logging settings

Logging settings are configured using the `pykour.logging` key.

### Logging level setting

Logging levels are set using the `level` key.

```yaml
pykour:
  logging:
    level: INFO, DEBUG
```

Pykour does not filter by level in general, but by enumerating the levels to be covered.
In this example, in addition to the explicitly specified `INFO` and `DEBUG` logs, the access log is also output.

## Database Settings

Database settings are configured using the `pykour.datasource` key.

### Database type setting

Database type is set using the `type` key.

```yaml
pykour:
  datasource:
    type: sqlite
```

### Settings database connection information

Use `host`, `db`, `username`, and `password` to set database connection information.

```yaml
pykour:
  datasource:
    type: mysql
    host: localhost
    db: test
    username: root
    password: password
```

The available settings are as follows:

- `host`: Database hostname
- `db`: Database name
- `username`: Username
- `password`: Password

### connection pool settings

Use the `pool` key to set up a connection pool.

```yaml
pykour:
  datasource:
    type: mysql
    host: localhost
    db: test
    username: root
    password: password
    pool:
      max-connections: 10
```

To set up a connection pool, specify the maximum pool size with the `max-connections` key.
