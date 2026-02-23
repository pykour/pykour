# Configuration

Pykour supports TOML-based configuration with environment variable overrides. Configuration is loaded with a clear priority order, allowing you to define defaults in a file and override them per environment.

## Configuration Priority

Configuration is resolved in the following order (highest priority first):

1. **Environment variables** (e.g., `PYKOUR_DATABASE_URL`)
2. **Constructor parameters** (explicit code values)
3. **`PYKOUR_CONFIG_FILE` env var** (path to config file)
4. **Auto-discovered `pykour.toml`** in the current working directory
5. **Default values**

## Configuration File

By default, Pykour auto-discovers a `pykour.toml` file in the current working directory. You can also specify a path explicitly:

```python
from pykour import Pykour

# Auto-discover pykour.toml
app = Pykour(routes_dir="routes")

# Explicit config file
app = Pykour(routes_dir="routes", config_file="config/pykour.toml")

# Disable auto-discovery
app = Pykour(routes_dir="routes", auto_load_config=False)
```

## Full Configuration Reference

### `[app]` -- Application Settings

```toml
[app]
routes_dir = "routes"
debug = false
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `routes_dir` | `str` | `"routes"` | Directory containing route files. |
| `debug` | `bool` | `false` | Enable debug mode. |

### `[database]` -- Database Connection

```toml
[database]
url = "sqlite:///app.db"
min_size = 1
max_size = 10
enable_access_policies = true
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `url` | `str` | -- | Database connection URL. |
| `min_size` | `int` | `1` | Minimum connection pool size. |
| `max_size` | `int` | `10` | Maximum connection pool size. |
| `enable_access_policies` | `bool` | `true` | Enable row-level access policies. |

### `[cache]` -- Cache Storage

```toml
[cache]
url = "valkey://localhost:6379"
prefix = "pykour:"
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `url` | `str` | -- | Valkey/Redis connection URL. If not set, cache is disabled. |
| `prefix` | `str` | `"pykour:"` | Key prefix for all cache keys. |

### `[logging]` -- Logging

```toml
[logging]
format = "text"
level = "INFO"
logger_name = "pykour.access"
log_request_headers = false
log_response_headers = false
```

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `format` | `"text" \| "json"` | `"text"` | Log output format. |
| `level` | `str` | `"INFO"` | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL). |
| `logger_name` | `str` | `"pykour.access"` | Logger name. |
| `log_request_headers` | `bool` | `false` | Include request headers in logs. |
| `log_response_headers` | `bool` | `false` | Include response headers in logs. |

### `[openapi]` -- OpenAPI Documentation

```toml
[openapi]
title = "My API"
version = "1.0.0"
description = "API description"
docs_url = "/docs"
openapi_url = "/openapi.json"
redoc_url = "/redoc"
```

See the [OpenAPI page](openapi.md) for full configuration details including contact, license, and server settings.

### `[health]` -- Health Check

```toml
[health]
health_url = "/health"
include_details = false
```

See the [Health Checks page](health-checks.md) for details.

### `[metrics]` -- Metrics

```toml
[metrics]
metrics_url = "/metrics"
normalize_paths = true
namespace = ""
subsystem = "http"
```

See the [Metrics page](metrics.md) for details.

### `[middleware]` -- Middleware Configuration

Middleware can be configured via TOML sections. See the Middleware documentation for the full reference. Example:

```toml
[middleware.cors]
allow_origins = ["https://example.com"]
allow_methods = ["GET", "POST"]

[middleware.jwt]
secret_key = "${JWT_SECRET_KEY}"
algorithm = "HS256"

[middleware.rate_limit]
requests = 100
window = 60
```

## Environment Variables

The following environment variables override corresponding config file values:

| Variable | Config Path | Type |
|----------|------------|------|
| `PYKOUR_DEBUG` | `app.debug` | `bool` |
| `PYKOUR_ROUTES_DIR` | `app.routes_dir` | `str` |
| `PYKOUR_DATABASE_URL` | `database.url` | `str` |
| `PYKOUR_CACHE_URL` | `cache.url` | `str` |
| `PYKOUR_LOG_LEVEL` | `logging.level` | `str` |
| `PYKOUR_LOG_FORMAT` | `logging.format` | `str` |
| `PYKOUR_JWT_SECRET_KEY` | `middleware.jwt.secret_key` | `str` |
| `PYKOUR_CONFIG_FILE` | Config file path | `str` |

### Environment Variable Expansion in TOML

You can reference environment variables inside TOML values using `${VAR_NAME}` syntax:

```toml
[database]
url = "${DATABASE_URL}"

[middleware.jwt]
secret_key = "${JWT_SECRET_KEY}"
```

## PykourConfig Structure

The root configuration object:

```python
@dataclass
class PykourConfig:
    app: AppConfig
    openapi: OpenAPIConfigModel
    health: HealthConfig
    metrics: MetricsConfigModel
    database: DatabaseConfig
    cache: CacheConfig
    logging: LoggingConfig
    middleware: MiddlewareConfig
```

## Loading Configuration Programmatically

```python
from pykour.config import load_config

# Load with defaults
config = load_config()

# Load from specific file
config = load_config(config_file="custom.toml")

# Load without auto-discovery
config = load_config(auto_discover=False)
```
