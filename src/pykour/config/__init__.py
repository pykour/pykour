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

from pykour.config.loader import find_config_file, load_config
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
