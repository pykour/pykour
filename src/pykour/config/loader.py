"""TOML configuration file loading for Pykour."""

import os
import re
import tomllib
from pathlib import Path
from typing import Any

from pykour.config.env import apply_env_overrides
from pykour.config.models import (
    AppConfig,
    CacheConfig,
    CORSMiddlewareConfig,
    CSPConfig,
    CSRFMiddlewareConfig,
    DatabaseConfig,
    HealthConfig,
    JWTMiddlewareConfig,
    LoggingConfig,
    LoggingMiddlewareConfig,
    MetricsConfigModel,
    MiddlewareConfig,
    OpenAPIConfigModel,
    OpenAPIContactConfig,
    OpenAPILicenseConfig,
    OpenAPIServerConfig,
    PykourConfig,
    RateLimitMiddlewareConfig,
    RateLimitPathConfig,
    SecurityMiddlewareConfig,
    SizeLimitMiddlewareConfig,
    TraceMiddlewareConfig,
)

# Default config file name
DEFAULT_CONFIG_FILE = "pykour.toml"

# Pattern to match ${VAR} or ${VAR:-default} format
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def expand_env_vars(value: str) -> str:
    """Expand environment variables in a string.

    Supports two formats:
    - ${VAR}: Expands to the value of VAR, or empty string if not set
    - ${VAR:-default}: Expands to the value of VAR, or 'default' if not set

    Args:
        value: String potentially containing environment variable references

    Returns:
        String with environment variables expanded
    """

    def replace_match(match: re.Match[str]) -> str:
        var_name = match.group(1)
        default_value = match.group(2)
        env_value = os.environ.get(var_name)
        if env_value is not None:
            return env_value
        if default_value is not None:
            return default_value
        return ""

    return ENV_VAR_PATTERN.sub(replace_match, value)


def expand_env_vars_recursive(data: Any) -> Any:
    """Recursively expand environment variables in nested data structures.

    Args:
        data: Any data structure (dict, list, str, etc.)

    Returns:
        Data structure with environment variables expanded in all strings
    """
    if isinstance(data, str):
        return expand_env_vars(data)
    if isinstance(data, dict):
        return {key: expand_env_vars_recursive(value) for key, value in data.items()}
    if isinstance(data, list):
        return [expand_env_vars_recursive(item) for item in data]
    return data


def find_config_file(start_dir: Path | None = None) -> Path | None:
    """Find pykour.toml in current or parent directories.

    Args:
        start_dir: Directory to start searching from. Defaults to cwd.

    Returns:
        Path to config file if found, None otherwise.
    """
    if start_dir is None:
        try:
            start_dir = Path.cwd()
        except (FileNotFoundError, OSError):
            # cwd() can fail if current directory was deleted
            return None

    try:
        current = start_dir.resolve()
    except (FileNotFoundError, OSError):
        return None

    # Search up to root
    while current != current.parent:
        config_path = current / DEFAULT_CONFIG_FILE
        if config_path.exists():
            return config_path
        current = current.parent

    # Check root
    config_path = current / DEFAULT_CONFIG_FILE
    if config_path.exists():
        return config_path

    return None


def load_toml(path: Path, expand_env: bool = True) -> dict[str, Any]:
    """Load TOML file with optional environment variable expansion.

    Args:
        path: Path to TOML file
        expand_env: Whether to expand ${VAR} and ${VAR:-default} patterns

    Returns:
        Parsed TOML data as dictionary with environment variables expanded
    """
    with open(path, "rb") as f:
        data = tomllib.load(f)
    if expand_env:
        data = expand_env_vars_recursive(data)
    return data


def _parse_app_config(data: dict[str, Any]) -> AppConfig:
    """Parse app section."""
    return AppConfig(
        routes_dir=data.get("routes_dir", "routes"),
        debug=data.get("debug", False),
    )


def _parse_openapi_contact(data: dict[str, Any] | None) -> OpenAPIContactConfig | None:
    """Parse openapi.contact section."""
    if data is None:
        return None
    return OpenAPIContactConfig(
        name=data.get("name"),
        url=data.get("url"),
        email=data.get("email"),
    )


def _parse_openapi_license(data: dict[str, Any] | None) -> OpenAPILicenseConfig | None:
    """Parse openapi.license section."""
    if data is None:
        return None
    return OpenAPILicenseConfig(
        name=data.get("name"),
        identifier=data.get("identifier"),
        url=data.get("url"),
    )


def _parse_openapi_servers(
    data: list[dict[str, Any]] | None,
) -> list[OpenAPIServerConfig]:
    """Parse openapi.servers section."""
    if data is None:
        return []
    return [
        OpenAPIServerConfig(
            url=server["url"],
            description=server.get("description"),
        )
        for server in data
    ]


def _parse_openapi_config(data: dict[str, Any]) -> OpenAPIConfigModel:
    """Parse openapi section."""
    return OpenAPIConfigModel(
        title=data.get("title", "Pykour API"),
        version=data.get("version", "1.0.0"),
        description=data.get("description"),
        docs_url=data.get("docs_url", "/docs"),
        openapi_url=data.get("openapi_url", "/openapi.json"),
        redoc_url=data.get("redoc_url", "/redoc"),
        contact=_parse_openapi_contact(data.get("contact")),
        license=_parse_openapi_license(data.get("license")),
        servers=_parse_openapi_servers(data.get("servers")),
    )


def _parse_health_config(data: dict[str, Any]) -> HealthConfig:
    """Parse health section."""
    return HealthConfig(
        url=data.get("url", "/health"),
        include_details=data.get("include_details", False),
        version=data.get("version"),
    )


def _parse_metrics_config(data: dict[str, Any]) -> MetricsConfigModel:
    """Parse metrics section."""
    return MetricsConfigModel(
        url=data.get("url", "/metrics"),
        enabled=data.get("enabled", False),
        exclude_paths=data.get("exclude_paths", ["/health", "/metrics"]),
        namespace=data.get("namespace", ""),
        subsystem=data.get("subsystem", "http"),
        normalize_paths=data.get("normalize_paths", True),
    )


def _parse_database_config(data: dict[str, Any]) -> DatabaseConfig:
    """Parse database section."""
    return DatabaseConfig(
        url=data.get("url"),
        min_size=data.get("min_size", 1),
        max_size=data.get("max_size", 10),
        enable_access_policies=data.get("enable_access_policies", True),
    )


def _parse_cache_config(data: dict[str, Any]) -> CacheConfig:
    """Parse cache section."""
    return CacheConfig(
        url=data.get("url"),
        prefix=data.get("prefix", "pykour:"),
    )


def _parse_logging_config(data: dict[str, Any]) -> LoggingConfig:
    """Parse logging section."""
    return LoggingConfig(
        format=data.get("format", "text"),
        level=data.get("level", "INFO"),
        logger_name=data.get("logger_name", "pykour.access"),
        log_request_headers=data.get("log_request_headers", False),
        log_response_headers=data.get("log_response_headers", False),
    )


def _parse_cors_middleware(data: dict[str, Any]) -> CORSMiddlewareConfig:
    """Parse middleware.cors section."""
    return CORSMiddlewareConfig(
        enabled=data.get("enabled", False),
        allow_origins=data.get("allow_origins", []),
        allow_methods=data.get("allow_methods", ["GET"]),
        allow_headers=data.get("allow_headers", []),
        allow_credentials=data.get("allow_credentials", False),
        expose_headers=data.get("expose_headers", []),
        max_age=data.get("max_age", 600),
    )


def _parse_jwt_middleware(data: dict[str, Any]) -> JWTMiddlewareConfig:
    """Parse middleware.jwt section."""
    return JWTMiddlewareConfig(
        enabled=data.get("enabled", False),
        secret_key=data.get("secret_key"),
        secret_keys=data.get("secret_keys"),
        algorithm=data.get("algorithm", "HS256"),
        exclude_paths=data.get("exclude_paths", []),
        auto_error=data.get("auto_error", True),
    )


def _parse_rate_limit_path_configs(
    data: dict[str, Any] | None,
) -> dict[str, RateLimitPathConfig]:
    """Parse middleware.rate_limit.path_configs section."""
    if data is None:
        return {}
    return {
        path: RateLimitPathConfig(
            requests_per_second=config["requests_per_second"],
            burst_size=config["burst_size"],
        )
        for path, config in data.items()
    }


def _parse_rate_limit_middleware(data: dict[str, Any]) -> RateLimitMiddlewareConfig:
    """Parse middleware.rate_limit section."""
    return RateLimitMiddlewareConfig(
        enabled=data.get("enabled", False),
        requests_per_second=data.get("requests_per_second", 10.0),
        burst_size=data.get("burst_size", 20),
        exclude_paths=data.get("exclude_paths", []),
        include_headers=data.get("include_headers", True),
        path_configs=_parse_rate_limit_path_configs(data.get("path_configs")),
    )


def _parse_csp_config(data: dict[str, Any] | None) -> CSPConfig | None:
    """Parse middleware.security.csp section."""
    if data is None:
        return None
    return CSPConfig(
        default_src=data.get("default_src", ["'self'"]),
        script_src=data.get("script_src"),
        style_src=data.get("style_src"),
        img_src=data.get("img_src"),
        font_src=data.get("font_src"),
        connect_src=data.get("connect_src"),
        media_src=data.get("media_src"),
        object_src=data.get("object_src"),
        frame_src=data.get("frame_src"),
        frame_ancestors=data.get("frame_ancestors"),
        form_action=data.get("form_action"),
        base_uri=data.get("base_uri"),
    )


def _parse_security_middleware(data: dict[str, Any]) -> SecurityMiddlewareConfig:
    """Parse middleware.security section."""
    return SecurityMiddlewareConfig(
        enabled=data.get("enabled", False),
        hsts_max_age=data.get("hsts_max_age", 31536000),
        hsts_include_subdomains=data.get("hsts_include_subdomains", True),
        hsts_preload=data.get("hsts_preload", False),
        x_content_type_options=data.get("x_content_type_options", "nosniff"),
        x_frame_options=data.get("x_frame_options", "DENY"),
        x_xss_protection=data.get("x_xss_protection", "0"),
        referrer_policy=data.get("referrer_policy", "strict-origin-when-cross-origin"),
        csp=_parse_csp_config(data.get("csp")),
        csp_report_only=data.get("csp_report_only", False),
        exclude_paths=data.get("exclude_paths", []),
    )


def _parse_csrf_middleware(data: dict[str, Any]) -> CSRFMiddlewareConfig:
    """Parse middleware.csrf section."""
    return CSRFMiddlewareConfig(
        enabled=data.get("enabled", False),
        cookie_name=data.get("cookie_name", "csrf_token"),
        header_name=data.get("header_name", "X-CSRF-Token"),
        cookie_path=data.get("cookie_path", "/"),
        cookie_domain=data.get("cookie_domain"),
        cookie_secure=data.get("cookie_secure", False),
        cookie_httponly=data.get("cookie_httponly", False),
        cookie_samesite=data.get("cookie_samesite", "Lax"),
        cookie_max_age=data.get("cookie_max_age", 86400),
        exclude_paths=data.get("exclude_paths", []),
    )


def _parse_size_limit_middleware(data: dict[str, Any]) -> SizeLimitMiddlewareConfig:
    """Parse middleware.size_limit section."""
    return SizeLimitMiddlewareConfig(
        enabled=data.get("enabled", False),
        max_size=data.get("max_size", 1048576),
        max_size_by_content_type=data.get("max_size_by_content_type", {}),
        exclude_paths=data.get("exclude_paths", []),
        check_content_length=data.get("check_content_length", True),
        check_body_size=data.get("check_body_size", True),
    )


def _parse_logging_middleware(data: dict[str, Any]) -> LoggingMiddlewareConfig:
    """Parse middleware.logging section."""
    return LoggingMiddlewareConfig(
        enabled=data.get("enabled", False),
        format=data.get("format", "text"),
        level=data.get("level", "INFO"),
        logger_name=data.get("logger_name", "pykour.access"),
        exclude_paths=data.get("exclude_paths", []),
        log_request_headers=data.get("log_request_headers", False),
        log_response_headers=data.get("log_response_headers", False),
    )


def _parse_trace_middleware(data: dict[str, Any]) -> TraceMiddlewareConfig:
    """Parse middleware.trace section."""
    return TraceMiddlewareConfig(
        enabled=data.get("enabled", False),
    )


def _parse_middleware_config(data: dict[str, Any]) -> MiddlewareConfig:
    """Parse middleware section."""
    return MiddlewareConfig(
        cors=_parse_cors_middleware(data.get("cors", {})),
        jwt=_parse_jwt_middleware(data.get("jwt", {})),
        rate_limit=_parse_rate_limit_middleware(data.get("rate_limit", {})),
        security=_parse_security_middleware(data.get("security", {})),
        csrf=_parse_csrf_middleware(data.get("csrf", {})),
        size_limit=_parse_size_limit_middleware(data.get("size_limit", {})),
        logging=_parse_logging_middleware(data.get("logging", {})),
        trace=_parse_trace_middleware(data.get("trace", {})),
    )


def dict_to_config(data: dict[str, Any]) -> PykourConfig:
    """Convert dictionary to PykourConfig.

    Args:
        data: Dictionary from parsed TOML file

    Returns:
        PykourConfig instance
    """
    return PykourConfig(
        app=_parse_app_config(data.get("app", {})),
        openapi=_parse_openapi_config(data.get("openapi", {})),
        health=_parse_health_config(data.get("health", {})),
        metrics=_parse_metrics_config(data.get("metrics", {})),
        database=_parse_database_config(data.get("database", {})),
        cache=_parse_cache_config(data.get("cache", {})),
        logging=_parse_logging_config(data.get("logging", {})),
        middleware=_parse_middleware_config(data.get("middleware", {})),
    )


def load_config(
    config_file: str | Path | None = None,
    auto_discover: bool = True,
) -> PykourConfig:
    """Load configuration with priority.

    Priority (highest to lowest):
    1. Environment variables
    2. Explicit config_file parameter
    3. PYKOUR_CONFIG_FILE env var
    4. Auto-discovered pykour.toml (if auto_discover=True)
    5. Default values

    Args:
        config_file: Explicit path to config file
        auto_discover: Whether to auto-discover pykour.toml

    Returns:
        PykourConfig instance with merged configuration
    """
    config = PykourConfig()  # Start with defaults

    # Determine config file path
    file_path: Path | None = None

    if config_file is not None:
        file_path = Path(config_file)
    elif env_config := os.environ.get("PYKOUR_CONFIG_FILE"):
        file_path = Path(env_config)
    elif auto_discover:
        file_path = find_config_file()

    # Load from file if found
    if file_path is not None and file_path.exists():
        toml_data = load_toml(file_path)
        config = dict_to_config(toml_data)

    # Apply environment variable overrides (highest priority)
    config = apply_env_overrides(config)

    return config
