# Health Checks

Pykour provides a built-in health check endpoint for use with load balancers, Kubernetes probes, and monitoring systems.

## Default Endpoint

The health check endpoint is enabled by default at `/health`:

```python
from pykour import Pykour

app = Pykour(routes_dir="routes")
# GET /health returns {"status": "healthy"}
```

### Disabling

```python
app = Pykour(routes_dir="routes", health_url=None)
```

### Custom URL

```python
app = Pykour(routes_dir="routes", health_url="/healthz")
```

## HealthCheckConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `health_url` | `str \| None` | `"/health"` | URL path. `None` to disable. |
| `include_details` | `bool` | `False` | Include detailed check results in response. |
| `checks` | `list[HealthCheckFunc]` | `[]` | Custom health check functions. |
| `version` | `str \| None` | `None` | Application version to include in response. |

### TOML Configuration

```toml
[health]
health_url = "/health"
include_details = true
```

## Custom Health Checks

You can add custom health check functions that verify dependencies (database, cache, external services):

```python
from pykour.health.config import HealthCheckConfig

async def check_database():
    # Return a health status dict
    try:
        await db.execute("SELECT 1")
        return {"name": "database", "status": "healthy"}
    except Exception as e:
        return {"name": "database", "status": "unhealthy", "error": str(e)}

config = HealthCheckConfig(
    include_details=True,
    checks=[check_database],
)
```

## Response Format

### Basic Response (default)

```json
{
  "status": "healthy"
}
```

### Detailed Response (`include_details=True`)

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": [
    {
      "name": "database",
      "status": "healthy"
    }
  ]
}
```

## Kubernetes Integration

### Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Readiness Probe

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

For applications with database dependencies, you may want separate liveness and readiness endpoints. You can use the default `/health` for liveness and add custom health checks for readiness.

## Docker Healthcheck

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```
