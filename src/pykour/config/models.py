"""Configuration data classes for Pykour."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class AppConfig:
    """Application core configuration."""

    routes_dir: str = "routes"
    debug: bool = False


@dataclass
class OpenAPIContactConfig:
    """OpenAPI contact information."""

    name: str | None = None
    url: str | None = None
    email: str | None = None


@dataclass
class OpenAPILicenseConfig:
    """OpenAPI license information."""

    name: str | None = None
    identifier: str | None = None
    url: str | None = None


@dataclass
class OpenAPIServerConfig:
    """OpenAPI server information."""

    url: str
    description: str | None = None


@dataclass
class OpenAPIConfigModel:
    """OpenAPI documentation configuration."""

    title: str = "Pykour API"
    version: str = "1.0.0"
    description: str | None = None
    docs_url: str | None = "/docs"
    openapi_url: str | None = "/openapi.json"
    redoc_url: str | None = "/redoc"
    contact: OpenAPIContactConfig | None = None
    license: OpenAPILicenseConfig | None = None
    servers: list[OpenAPIServerConfig] = field(default_factory=list)


@dataclass
class HealthConfig:
    """Health check endpoint configuration."""

    url: str | None = "/health"
    include_details: bool = False
    version: str | None = None


@dataclass
class MetricsConfigModel:
    """Metrics endpoint configuration."""

    url: str | None = "/metrics"
    enabled: bool = False
    exclude_paths: list[str] = field(default_factory=lambda: ["/health", "/metrics"])
    namespace: str = ""
    subsystem: str = "http"
    normalize_paths: bool = True


@dataclass
class DatabaseConfig:
    """Database connection configuration."""

    url: str | None = None
    min_size: int = 1
    max_size: int = 10
    enable_access_policies: bool = True


@dataclass
class CacheConfig:
    """Cache storage configuration."""

    url: str | None = None
    prefix: str = "pykour:"


@dataclass
class LoggingConfig:
    """Logging configuration."""

    format: Literal["text", "json"] = "text"
    level: str = "INFO"
    logger_name: str = "pykour.access"
    log_request_headers: bool = False
    log_response_headers: bool = False


@dataclass
class CORSMiddlewareConfig:
    """CORS middleware configuration."""

    enabled: bool = False
    allow_origins: list[str] = field(default_factory=list)
    allow_methods: list[str] = field(default_factory=lambda: ["GET"])
    allow_headers: list[str] = field(default_factory=list)
    allow_credentials: bool = False
    expose_headers: list[str] = field(default_factory=list)
    max_age: int = 600


@dataclass
class JWTMiddlewareConfig:
    """JWT authentication middleware configuration."""

    enabled: bool = False
    secret_key: str | None = None
    secret_keys: list[str] | None = None
    algorithm: str = "HS256"
    exclude_paths: list[str] = field(default_factory=list)
    auto_error: bool = True


@dataclass
class RateLimitPathConfig:
    """Rate limit configuration for a specific path."""

    requests_per_second: float
    burst_size: int


@dataclass
class RateLimitMiddlewareConfig:
    """Rate limiting middleware configuration."""

    enabled: bool = False
    requests_per_second: float = 10.0
    burst_size: int = 20
    exclude_paths: list[str] = field(default_factory=list)
    include_headers: bool = True
    path_configs: dict[str, RateLimitPathConfig] = field(default_factory=dict)


@dataclass
class CSPConfig:
    """Content Security Policy configuration."""

    default_src: list[str] = field(default_factory=lambda: ["'self'"])
    script_src: list[str] | None = None
    style_src: list[str] | None = None
    img_src: list[str] | None = None
    font_src: list[str] | None = None
    connect_src: list[str] | None = None
    media_src: list[str] | None = None
    object_src: list[str] | None = None
    frame_src: list[str] | None = None
    frame_ancestors: list[str] | None = None
    form_action: list[str] | None = None
    base_uri: list[str] | None = None


@dataclass
class SecurityMiddlewareConfig:
    """Security headers middleware configuration."""

    enabled: bool = False
    hsts_max_age: int | None = 31536000
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False
    x_content_type_options: str | None = "nosniff"
    x_frame_options: str | None = "DENY"
    x_xss_protection: str | None = "0"
    referrer_policy: str | None = "strict-origin-when-cross-origin"
    csp: CSPConfig | None = None
    csp_report_only: bool = False
    exclude_paths: list[str] = field(default_factory=list)


@dataclass
class CSRFMiddlewareConfig:
    """CSRF protection middleware configuration."""

    enabled: bool = False
    cookie_name: str = "csrf_token"
    header_name: str = "X-CSRF-Token"
    cookie_path: str = "/"
    cookie_domain: str | None = None
    cookie_secure: bool = False
    cookie_httponly: bool = False
    cookie_samesite: str = "Lax"
    cookie_max_age: int = 86400
    exclude_paths: list[str] = field(default_factory=list)


@dataclass
class SizeLimitMiddlewareConfig:
    """Request size limit middleware configuration."""

    enabled: bool = False
    max_size: int = 1048576  # 1MB
    max_size_by_content_type: dict[str, int] = field(default_factory=dict)
    exclude_paths: list[str] = field(default_factory=list)
    check_content_length: bool = True
    check_body_size: bool = True


@dataclass
class LoggingMiddlewareConfig:
    """Access logging middleware configuration."""

    enabled: bool = False
    format: Literal["text", "json"] = "text"
    level: str = "INFO"
    logger_name: str = "pykour.access"
    exclude_paths: list[str] = field(default_factory=list)
    log_request_headers: bool = False
    log_response_headers: bool = False


@dataclass
class TraceMiddlewareConfig:
    """Trace ID middleware configuration."""

    enabled: bool = False


@dataclass
class MiddlewareConfig:
    """Container for all middleware configurations."""

    cors: CORSMiddlewareConfig = field(default_factory=CORSMiddlewareConfig)
    jwt: JWTMiddlewareConfig = field(default_factory=JWTMiddlewareConfig)
    rate_limit: RateLimitMiddlewareConfig = field(
        default_factory=RateLimitMiddlewareConfig
    )
    security: SecurityMiddlewareConfig = field(default_factory=SecurityMiddlewareConfig)
    csrf: CSRFMiddlewareConfig = field(default_factory=CSRFMiddlewareConfig)
    size_limit: SizeLimitMiddlewareConfig = field(
        default_factory=SizeLimitMiddlewareConfig
    )
    logging: LoggingMiddlewareConfig = field(default_factory=LoggingMiddlewareConfig)
    trace: TraceMiddlewareConfig = field(default_factory=TraceMiddlewareConfig)


@dataclass
class PykourConfig:
    """Root configuration container for Pykour application."""

    app: AppConfig = field(default_factory=AppConfig)
    openapi: OpenAPIConfigModel = field(default_factory=OpenAPIConfigModel)
    health: HealthConfig = field(default_factory=HealthConfig)
    metrics: MetricsConfigModel = field(default_factory=MetricsConfigModel)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    middleware: MiddlewareConfig = field(default_factory=MiddlewareConfig)
