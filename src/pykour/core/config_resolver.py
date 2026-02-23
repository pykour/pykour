"""Configuration resolution for Pykour application."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from pykour.cache.storage import CacheStorage
    from pykour.config import PykourConfig
    from pykour.db import Database
    from pykour.health.config import HealthCheckConfig
    from pykour.metrics.config import MetricsConfig
    from pykour.openapi.config import OpenAPIConfig, SecuritySchemeConfig


# Sentinel value to indicate that routes_dir should be resolved from the caller's directory
_CALLER_ROUTES_DIR: object = object()

# Sentinel value to indicate "use config file default"
_USE_CONFIG_DEFAULT: object = object()


@dataclass
class ResolvedConfig:
    """Fully resolved application configuration.

    This dataclass holds all resolved configuration values after
    merging code, environment, and config file settings.
    """

    routes_dir: Path
    debug: bool
    database: "Database | None"
    cache: "CacheStorage | None"
    openapi_config: "OpenAPIConfig"
    health_config: "HealthCheckConfig"
    metrics_config: "MetricsConfig"


def resolve_routes_dir(
    routes_dir: str | Path | None,
    config: "PykourConfig",
    caller_stack_level: int = 3,
) -> Path:
    """Resolve routes_dir to an absolute Path.

    Priority: code > config file > caller's directory

    Args:
        routes_dir: Explicitly specified routes directory, or None.
        config: Loaded configuration.
        caller_stack_level: Stack level to find the caller's file.

    Returns:
        Resolved Path to the routes directory.
    """
    if routes_dir is not None:
        return _resolve_path(routes_dir)

    if config.app.routes_dir != "routes":
        # Config file specified a non-default value
        return Path(config.app.routes_dir)

    # Use caller's directory as default
    return _resolve_from_caller(caller_stack_level)


def _resolve_path(routes_dir: str | Path | object) -> Path:
    """Resolve a routes_dir value to a Path.

    Args:
        routes_dir: Routes directory specification.

    Returns:
        Resolved Path.
    """
    if routes_dir is _CALLER_ROUTES_DIR:
        return _resolve_from_caller(3)
    return Path(routes_dir)  # type: ignore[arg-type]


def _resolve_from_caller(stack_level: int) -> Path:
    """Resolve routes_dir from the caller's directory.

    Args:
        stack_level: How many stack frames to go up.

    Returns:
        Path to "routes" subdirectory in caller's directory.
    """
    stack = inspect.stack()

    if len(stack) < stack_level:
        # Stack too shallow (unlikely but handle defensively)
        return Path.cwd() / "routes"

    caller_frame = stack[stack_level]
    caller_file = caller_frame.filename

    # Handle REPL or other non-file contexts
    if not caller_file or caller_file.startswith("<"):
        return Path.cwd() / "routes"

    caller_path = Path(caller_file)

    # Handle frozen executables or missing files
    if not caller_path.exists():
        return Path.cwd() / "routes"

    return caller_path.parent.resolve() / "routes"


def resolve_debug(debug: bool | None, config: "PykourConfig") -> bool:
    """Resolve debug mode setting.

    Priority: code > env/config

    Args:
        debug: Explicitly specified debug value, or None.
        config: Loaded configuration.

    Returns:
        Resolved debug mode.
    """
    if debug is not None:
        return debug
    return config.app.debug


def resolve_database(
    database: "Database | None",
    config: "PykourConfig",
) -> "Database | None":
    """Resolve database instance.

    Priority: explicit > config file

    Args:
        database: Explicitly specified database instance, or None.
        config: Loaded configuration.

    Returns:
        Resolved database instance or None.
    """
    if database is not None:
        return database

    if config.database.url:
        from pykour.db.database import Database as DatabaseClass

        return DatabaseClass(
            url=config.database.url,
            min_size=config.database.min_size,
            max_size=config.database.max_size,
            enable_access_policies=config.database.enable_access_policies,
        )

    return None


def resolve_cache(
    cache: "CacheStorage | None",
    config: "PykourConfig",
) -> "CacheStorage | None":
    """Resolve cache storage instance.

    Priority: explicit > config file

    Args:
        cache: Explicitly specified cache storage, or None.
        config: Loaded configuration.

    Returns:
        Resolved cache storage or None.
    """
    if cache is not None:
        return cache

    if config.cache.url:
        from pykour.cache.valkey import ValkeyStorage

        return ValkeyStorage(
            url=config.cache.url,
            prefix=config.cache.prefix,
        )

    return None


def resolve_openapi_config(
    config: "PykourConfig",
    title: str | None = None,
    version: str | None = None,
    description: str | None = None,
    docs_url: str | None | object = _USE_CONFIG_DEFAULT,
    openapi_url: str | None | object = _USE_CONFIG_DEFAULT,
    redoc_url: str | None | object = _USE_CONFIG_DEFAULT,
    security_schemes: "dict[str, SecuritySchemeConfig] | None" = None,
    global_security: "list[dict[str, list[str]]] | None" = None,
) -> "OpenAPIConfig":
    """Resolve OpenAPI configuration.

    Priority: code > config file

    Args:
        config: Loaded configuration.
        title: API title.
        version: API version.
        description: API description.
        docs_url: Swagger UI URL.
        openapi_url: OpenAPI JSON URL.
        redoc_url: ReDoc URL.
        security_schemes: Security scheme configurations for OpenAPI documentation.
        global_security: Global security requirements applied to all operations.

    Returns:
        Resolved OpenAPI configuration.
    """
    from pykour.openapi.config import OpenAPIConfig

    resolved_title = title if title is not None else config.openapi.title
    resolved_version = version if version is not None else config.openapi.version
    resolved_description = (
        description if description is not None else config.openapi.description
    )
    resolved_docs_url: str | None = (
        config.openapi.docs_url
        if docs_url is _USE_CONFIG_DEFAULT
        else cast("str | None", docs_url)
    )
    resolved_openapi_url: str | None = (
        config.openapi.openapi_url
        if openapi_url is _USE_CONFIG_DEFAULT
        else cast("str | None", openapi_url)
    )
    resolved_redoc_url: str | None = (
        config.openapi.redoc_url
        if redoc_url is _USE_CONFIG_DEFAULT
        else cast("str | None", redoc_url)
    )

    return OpenAPIConfig(
        title=resolved_title,
        version=resolved_version,
        description=resolved_description,
        docs_url=resolved_docs_url,
        openapi_url=resolved_openapi_url,
        redoc_url=resolved_redoc_url,
        security_schemes=security_schemes,
        global_security=global_security,
    )


def resolve_health_config(
    config: "PykourConfig",
    health_url: str | None | object = _USE_CONFIG_DEFAULT,
) -> "HealthCheckConfig":
    """Resolve health check configuration.

    Priority: code > config file

    Args:
        config: Loaded configuration.
        health_url: Health check endpoint URL.

    Returns:
        Resolved health check configuration.
    """
    from pykour.health.config import HealthCheckConfig

    resolved_health_url: str | None = (
        config.health.url
        if health_url is _USE_CONFIG_DEFAULT
        else cast("str | None", health_url)
    )

    return HealthCheckConfig(health_url=resolved_health_url)


def resolve_metrics_config(
    config: "PykourConfig",
    health_url: str | None,
    metrics_url: str | None | object = _USE_CONFIG_DEFAULT,
) -> "MetricsConfig":
    """Resolve metrics configuration.

    Priority: code > config file

    Args:
        config: Loaded configuration.
        health_url: Health check endpoint URL (to exclude from metrics).
        metrics_url: Metrics endpoint URL.

    Returns:
        Resolved metrics configuration.
    """
    from pykour.metrics.config import MetricsConfig

    resolved_metrics_url: str | None = (
        config.metrics.url
        if metrics_url is _USE_CONFIG_DEFAULT
        else cast("str | None", metrics_url)
    )

    # Build exclude paths list
    metrics_exclude_paths = ["/metrics"]
    if health_url is not None:
        metrics_exclude_paths.append(health_url)
    if resolved_metrics_url is not None and resolved_metrics_url != "/metrics":
        metrics_exclude_paths.append(resolved_metrics_url)

    return MetricsConfig(
        metrics_url=resolved_metrics_url,
        exclude_paths=metrics_exclude_paths,
    )


# Re-export sentinel values for use by application.py
__all__ = [
    "ResolvedConfig",
    "resolve_routes_dir",
    "resolve_debug",
    "resolve_database",
    "resolve_cache",
    "resolve_openapi_config",
    "resolve_health_config",
    "resolve_metrics_config",
    "_CALLER_ROUTES_DIR",
    "_USE_CONFIG_DEFAULT",
]
