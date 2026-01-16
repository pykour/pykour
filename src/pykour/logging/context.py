"""Trace context management using contextvars.

This module provides request-scoped trace ID management for correlating
logs across a single request lifecycle.

Example:
    from pykour.logging.context import get_trace_id, set_trace_id

    # In middleware
    set_trace_id("abc-123")

    # In handler or anywhere in the request
    trace_id = get_trace_id()  # Returns "abc-123"
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

# Request-scoped trace ID storage
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def get_trace_id() -> str | None:
    """Get the current request's trace ID.

    Returns:
        The trace ID if in a request context, None otherwise.

    Example:
        trace_id = get_trace_id()
        if trace_id:
            logger.info(f"Processing request {trace_id}")
    """
    return _trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """Set the trace ID for the current request context.

    Args:
        trace_id: The trace ID to set.

    Note:
        This is typically called by TraceMiddleware at the start of a request.
    """
    _trace_id_var.set(trace_id)


def reset_trace_id() -> None:
    """Reset the trace ID to None.

    Note:
        This is typically called by TraceMiddleware at the end of a request.
    """
    _trace_id_var.set(None)


def generate_trace_id() -> str:
    """Generate a new trace ID using UUID v4.

    Returns:
        A new unique trace ID (UUID v4 hex string without hyphens).

    Example:
        trace_id = generate_trace_id()
        # Returns something like "4bf92f3577b34da6a3ce929d0e0e4736"
    """
    return uuid.uuid4().hex
