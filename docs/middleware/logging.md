---
title: Logging
parent: Middleware
nav_order: 6
---

# Logging

`LoggingMiddleware` provides structured access logging for HTTP requests, capturing method, path, status code, response time, and optionally headers. It supports both text and JSON output formats.

## Basic usage

```python
from pykour import Pykour
from pykour.middleware import LoggingMiddleware

app = Pykour()

app.add_middleware(LoggingMiddleware)
```

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `logger_name` | `str` | `"pykour.access"` | Name of the Python logger. |
| `level` | `str \| int` | `"INFO"` | Minimum log level (string name or integer). |
| `exclude_paths` | `Sequence[str]` | `()` | Paths to exclude from logging. |
| `log_request_headers` | `bool` | `False` | Include request headers in log output. |
| `log_response_headers` | `bool` | `False` | Include response headers in log output. |
| `format` | `"text" \| "json"` | `"text"` | Output format. |

## Output formats

### Text format (default)

```
INFO     GET /api/users 200 12.34ms
```

### JSON format

```python
app.add_middleware(
    LoggingMiddleware,
    format="json",
)
```

JSON output includes structured fields suitable for log aggregation tools.

## Log levels by status code

The middleware automatically adjusts the log level based on the HTTP status code:

| Status Range | Log Level |
|---|---|
| 2xx | Configured level (default `INFO`) |
| 3xx | Configured level (default `INFO`) |
| 4xx | `WARNING` |
| 5xx | `ERROR` |

## Header logging

Enable request and/or response header logging for debugging:

```python
app.add_middleware(
    LoggingMiddleware,
    log_request_headers=True,
    log_response_headers=True,
)
```

Sensitive headers (e.g., `Authorization`, `Cookie`) are automatically masked in log output.

## Excluding paths

Skip logging for health checks, metrics, or static asset paths:

```python
app.add_middleware(
    LoggingMiddleware,
    exclude_paths=["/health", "/metrics", "/static"],
)
```

## Integration with Python logging

The middleware uses Python's standard `logging` module. Configure the logger as needed:

```python
import logging

logging.basicConfig(level=logging.INFO)

# Or configure the specific logger
logger = logging.getLogger("pykour.access")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler("access.log")
logger.addHandler(handler)
```

Use `logger_name` to separate access logs from application logs:

```python
app.add_middleware(
    LoggingMiddleware,
    logger_name="myapp.access",
)
```

---
**See also:** [Tracing](./tracing.md) · [Middleware Overview](./index.md)
[← Back to Home](../index.md)
