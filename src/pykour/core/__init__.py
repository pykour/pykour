"""Core utilities for Pykour application.

This package contains modular components extracted from the main application:
- exceptions: Exception handling utilities
- handler: Request handling and caching utilities
- websocket: WebSocket connection handling
"""

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
from pykour.core.websocket import handle_websocket, inject_websocket_params

__all__ = [
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
    # websocket
    "handle_websocket",
    "inject_websocket_params",
]
