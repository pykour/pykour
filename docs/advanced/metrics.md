---
title: Metrics
parent: Advanced
nav_order: 6
---

# Metrics
{: .no_toc }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

Pykour provides Prometheus-compatible metrics collection that can be scraped by monitoring systems. Metrics are collected via middleware and exposed through a dedicated endpoint.

## Setup

Metrics require two steps: enabling the endpoint and activating the collection middleware.

```python
from pykour import Pykour

app = Pykour(
    routes_dir="routes",
    metrics_url="/metrics",  # Enable metrics endpoint (default)
)

# Activate metrics collection middleware
app.enable_metrics()
```

The `metrics_url` parameter controls the endpoint path. Set it to `None` to disable:

```python
app = Pykour(routes_dir="routes", metrics_url=None)  # Disabled
```

### TOML Configuration

```toml
[metrics]
metrics_url = "/metrics"
normalize_paths = true
namespace = "myapp"
subsystem = "http"
```

## MetricsConfig

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `metrics_url` | `str \| None` | `"/metrics"` | URL path for the metrics endpoint. `None` to disable. |
| `exclude_paths` | `list[str]` | `["/health", "/metrics"]` | Paths excluded from metrics collection. |
| `latency_buckets` | `tuple[float, ...]` | `(0.005, 0.01, ..., 10.0)` | Histogram bucket boundaries for latency (seconds). |
| `normalize_paths` | `bool` | `True` | Normalize paths to reduce cardinality (e.g., `/users/123` becomes `/users/{id}`). |
| `namespace` | `str` | `""` | Prefix for metric names. |
| `subsystem` | `str` | `"http"` | Subsystem name for metric names. |

## Default Latency Buckets

The default histogram buckets (in seconds):

```
0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0
```

## Metrics Endpoint

The `/metrics` endpoint returns metrics in Prometheus text exposition format, suitable for scraping by Prometheus, Grafana Agent, or other compatible tools.

### Prometheus Configuration

```yaml
scrape_configs:
  - job_name: "pykour"
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: "/metrics"
    scrape_interval: 15s
```

## Excluding Paths

By default, `/health` and `/metrics` are excluded from metrics collection to avoid noise. You can customize this via the config:

```toml
[metrics]
exclude_paths = ["/health", "/metrics", "/docs", "/openapi.json"]
```

## Metric Naming

Metric names follow the Prometheus naming convention:

```
{namespace}_{subsystem}_request_duration_seconds
```

With default settings (empty namespace, `http` subsystem):

```
http_request_duration_seconds
```

With custom namespace:

```toml
[metrics]
namespace = "myapp"
subsystem = "api"
```

Results in:

```
myapp_api_request_duration_seconds
```

---

{: .fs-2 .text-muted }
Pykour Documentation
