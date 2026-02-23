"""Configuration module for Pykour.

This module provides configuration file support for Pykour applications.
Configuration can be loaded from TOML files (pykour.toml) with environment
variable overrides.

Example usage:
    # Auto-discover pykour.toml
    from pykour import Pykour
    app = Pykour()

    # Explicit config file
    app = Pykour(config_file="config/prod.toml")

    # Load config directly
    from pykour.config import load_config
    config = load_config("pykour.toml")
"""

from pykour.config.cli import (
    get_cli_config,
    get_config_value,
    get_database_url_from_config,
)
from pykour.config.loader import (
    expand_env_vars,
    expand_env_vars_recursive,
    find_config_file,
    load_config,
)
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

__all__ = [
    # Main config class
    "PykourConfig",
    # Loader functions
    "load_config",
    "find_config_file",
    "expand_env_vars",
    "expand_env_vars_recursive",
    # CLI functions
    "get_cli_config",
    "get_config_value",
    "get_database_url_from_config",
    # Section configs
    "AppConfig",
    "CacheConfig",
    "DatabaseConfig",
    "HealthConfig",
    "LoggingConfig",
    "MetricsConfigModel",
    "OpenAPIConfigModel",
    "OpenAPIContactConfig",
    "OpenAPILicenseConfig",
    "OpenAPIServerConfig",
    # Middleware configs
    "MiddlewareConfig",
    "CORSMiddlewareConfig",
    "CSPConfig",
    "CSRFMiddlewareConfig",
    "JWTMiddlewareConfig",
    "LoggingMiddlewareConfig",
    "RateLimitMiddlewareConfig",
    "RateLimitPathConfig",
    "SecurityMiddlewareConfig",
    "SizeLimitMiddlewareConfig",
    "TraceMiddlewareConfig",
]
