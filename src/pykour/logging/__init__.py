"""Pykour logging utilities.

This module provides logging utilities for request tracing and
structured log output.

Components:
    - TraceLogFilter: Logging filter that injects trace_id into log records
    - TextFormatter: Human-readable text format output
    - JsonFormatter: Machine-parseable JSON format output
    - get_trace_id: Get the current request's trace ID
    - set_trace_id: Set the trace ID for the current request
    - reset_trace_id: Clear the current request's trace ID
    - generate_trace_id: Generate a new trace ID (UUID v4)
    - sanitize_log_message: Mask sensitive information in log messages
    - sanitize_dict: Mask sensitive values in dictionaries

Example:
    import logging
    from pykour.logging import TraceLogFilter, JsonFormatter, get_trace_id

    # Configure logging with trace ID support
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceLogFilter())

    logger = logging.getLogger("myapp")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    # In a request handler
    logger.info("Processing user request")
    # Output: {"timestamp": "...", "trace_id": "abc-123", "type": "app", ...}

    # Access trace ID programmatically
    trace_id = get_trace_id()

    # Sanitize sensitive information
    from pykour.logging import sanitize_log_message
    safe_msg = sanitize_log_message('password="secret"')
    # Output: 'password="***"'
"""

from pykour.logging.context import (
    generate_trace_id,
    get_trace_id,
    reset_trace_id,
    set_trace_id,
)
from pykour.logging.filter import TraceLogFilter
from pykour.logging.formatter import JsonFormatter, TextFormatter
from pykour.logging.sanitizer import sanitize_dict, sanitize_log_message

__all__ = [
    "TraceLogFilter",
    "TextFormatter",
    "JsonFormatter",
    "get_trace_id",
    "set_trace_id",
    "reset_trace_id",
    "generate_trace_id",
    "sanitize_log_message",
    "sanitize_dict",
]
