"""Core utilities for Pykour application.

This package contains modular components extracted from the main application:
- config_resolver: Configuration resolution utilities
- exceptions: Exception handling utilities
- handler: Request handling and caching utilities
- lifespan: ASGI lifespan management
- middleware_builder: Middleware stack construction
- request_handler: HTTP request handling
- websocket: WebSocket connection handling
"""

from pykour.core.config_resolver import (
    ResolvedConfig,
    resolve_cache,
    resolve_database,
    resolve_debug,
    resolve_health_config,
    resolve_metrics_config,
    resolve_openapi_config,
    resolve_routes_dir,
)
from pykour.core.exceptions import (
    handle_exception,
    handle_http_exception,
    handle_unhandled_exception,
    handle_validation_exception,
)
from pykour.core.handler import (
    deserialize_response,
    interpolate_cache_key,
    interpolate_header_value,
    serialize_response,
)
from pykour.core.lifespan import LifespanManager
from pykour.core.middleware_builder import (
    MiddlewareBuilder,
    create_middleware_decorator,
)
from pykour.core.request_handler import RequestHandler
from pykour.core.websocket import handle_websocket, inject_websocket_params

__all__ = [
    # config_resolver
    "ResolvedConfig",
    "resolve_cache",
    "resolve_database",
    "resolve_debug",
    "resolve_health_config",
    "resolve_metrics_config",
    "resolve_openapi_config",
    "resolve_routes_dir",
    # exceptions
    "handle_exception",
    "handle_http_exception",
    "handle_unhandled_exception",
    "handle_validation_exception",
    # handler
    "deserialize_response",
    "interpolate_cache_key",
    "interpolate_header_value",
    "serialize_response",
    # lifespan
    "LifespanManager",
    # middleware_builder
    "MiddlewareBuilder",
    "create_middleware_decorator",
    # request_handler
    "RequestHandler",
    # websocket
    "handle_websocket",
    "inject_websocket_params",
]
