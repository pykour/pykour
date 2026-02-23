# Security Headers

`SecurityHeadersMiddleware` adds recommended security headers to HTTP responses, including HSTS, Content Security Policy, X-Frame-Options, and more.

## Basic usage

With no arguments, sensible defaults are applied:

```python
from pykour import Pykour
from pykour.middleware import SecurityHeadersMiddleware

app = Pykour()

app.add_middleware(SecurityHeadersMiddleware)
```

Default headers added:

| Header | Default Value |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `X-XSS-Protection` | `0` (disabled -- use CSP instead) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

## Constructor parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `hsts_max_age` | `int \| None` | `31536000` | HSTS max-age in seconds. `None` to disable. |
| `hsts_include_subdomains` | `bool` | `True` | Include subdomains in HSTS. |
| `hsts_preload` | `bool` | `False` | Enable HSTS preload. |
| `x_content_type_options` | `str \| None` | `"nosniff"` | X-Content-Type-Options value. |
| `x_frame_options` | `str \| None` | `"DENY"` | X-Frame-Options value (`DENY` or `SAMEORIGIN`). |
| `x_xss_protection` | `str \| None` | `"0"` | X-XSS-Protection value. |
| `referrer_policy` | `str \| None` | `"strict-origin-when-cross-origin"` | Referrer-Policy value. |
| `content_security_policy` | `ContentSecurityPolicy \| str \| None` | `None` | CSP configuration. |
| `csp_report_only` | `bool` | `False` | Use `Content-Security-Policy-Report-Only` header. |
| `permissions_policy` | `dict[str, list[str]] \| None` | `None` | Permissions-Policy directives. |
| `cross_origin_embedder_policy` | `str \| None` | `None` | COEP header value. |
| `cross_origin_opener_policy` | `str \| None` | `None` | COOP header value. |
| `cross_origin_resource_policy` | `str \| None` | `None` | CORP header value. |
| `cache_control` | `str \| None` | `None` | Cache-Control header value. |
| `exclude_paths` | `list[str] \| None` | `None` | Paths to exclude from header injection. |

Set any parameter to `None` to disable that header.

## Content Security Policy

Use `ContentSecurityPolicy` for structured CSP configuration:

```python
from pykour.middleware import SecurityHeadersMiddleware, ContentSecurityPolicy

csp = ContentSecurityPolicy(
    default_src=["'self'"],
    script_src=["'self'", "https://cdn.example.com"],
    style_src=["'self'", "'unsafe-inline'"],
    img_src=["'self'", "data:", "https:"],
    connect_src=["'self'", "https://api.example.com"],
    frame_ancestors=["'none'"],
    upgrade_insecure_requests=True,
)

app.add_middleware(
    SecurityHeadersMiddleware,
    content_security_policy=csp,
)
```

### ContentSecurityPolicy fields

| Field | Type | Default | Description |
|---|---|---|---|
| `default_src` | `list[str]` | `["'self'"]` | Default source directive. |
| `script_src` | `list[str] \| None` | `None` | Allowed script sources. |
| `style_src` | `list[str] \| None` | `None` | Allowed style sources. |
| `img_src` | `list[str] \| None` | `None` | Allowed image sources. |
| `font_src` | `list[str] \| None` | `None` | Allowed font sources. |
| `connect_src` | `list[str] \| None` | `None` | Allowed connection sources (fetch, XHR, WebSocket). |
| `media_src` | `list[str] \| None` | `None` | Allowed media sources. |
| `object_src` | `list[str] \| None` | `None` | Allowed object/embed sources. |
| `frame_src` | `list[str] \| None` | `None` | Allowed frame sources. |
| `frame_ancestors` | `list[str] \| None` | `None` | Allowed parent frames. |
| `form_action` | `list[str] \| None` | `None` | Allowed form action targets. |
| `base_uri` | `list[str] \| None` | `None` | Allowed base URIs. |
| `report_uri` | `str \| None` | `None` | CSP violation report URI. |
| `report_to` | `str \| None` | `None` | CSP violation report group. |
| `upgrade_insecure_requests` | `bool` | `False` | Upgrade HTTP to HTTPS. |
| `block_all_mixed_content` | `bool` | `False` | Block all mixed content. |

You can also pass CSP as a plain string:

```python
app.add_middleware(
    SecurityHeadersMiddleware,
    content_security_policy="default-src 'self'; script-src 'self' https://cdn.example.com",
)
```

### Report-only mode

Use `csp_report_only=True` to monitor violations without enforcing the policy:

```python
app.add_middleware(
    SecurityHeadersMiddleware,
    content_security_policy=csp,
    csp_report_only=True,
)
```

## Permissions Policy

```python
app.add_middleware(
    SecurityHeadersMiddleware,
    permissions_policy={
        "camera": [],           # Deny camera access
        "microphone": [],       # Deny microphone access
        "geolocation": ["self"],  # Allow only same-origin
    },
)
```

## Cross-origin policies

```python
app.add_middleware(
    SecurityHeadersMiddleware,
    cross_origin_embedder_policy="require-corp",
    cross_origin_opener_policy="same-origin",
    cross_origin_resource_policy="same-origin",
)
```

## Production example

```python
app.add_middleware(
    SecurityHeadersMiddleware,
    hsts_max_age=63072000,       # 2 years
    hsts_include_subdomains=True,
    hsts_preload=True,
    content_security_policy=ContentSecurityPolicy(
        default_src=["'self'"],
        script_src=["'self'"],
        style_src=["'self'"],
        img_src=["'self'", "data:"],
        frame_ancestors=["'none'"],
        upgrade_insecure_requests=True,
    ),
    permissions_policy={
        "camera": [],
        "microphone": [],
        "geolocation": [],
    },
    cache_control="no-store",
    exclude_paths=["/static"],
)
```

---
**See also:** [CORS](./cors.md) · [CSRF Protection](./csrf.md) · [Middleware Overview](./index.md)
[← Back to Home](../index.md)
