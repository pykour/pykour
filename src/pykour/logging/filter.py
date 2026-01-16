"""Logging filter for trace ID injection.

This module provides a logging filter that automatically injects
trace_id and log type into all log records.

Example:
    import logging
    from pykour.logging import TraceLogFilter

    handler = logging.StreamHandler()
    handler.addFilter(TraceLogFilter())
    logger = logging.getLogger("myapp")
    logger.addHandler(handler)

    # Now all log records will have trace_id and log_type attributes
    logger.info("Processing request")
"""

from __future__ import annotations

import logging

from pykour.logging.context import get_trace_id


class TraceLogFilter(logging.Filter):
    """Filter that injects trace_id and log_type into log records.

    This filter automatically adds:
    - trace_id: The current request's trace ID (or "-" if not in request context)
    - log_type: A type identifier for the log source (default: "app")

    Example:
        import logging
        from pykour.logging import TraceLogFilter

        # Basic usage
        handler = logging.StreamHandler()
        handler.addFilter(TraceLogFilter())

        # With custom log type
        handler.addFilter(TraceLogFilter(log_type="worker"))

    Attributes:
        log_type: The log type identifier added to records.
    """

    def __init__(
        self,
        name: str = "",
        log_type: str = "app",
    ) -> None:
        """Initialize the filter.

        Args:
            name: Filter name (standard logging.Filter parameter).
            log_type: Log type identifier (default: "app").
        """
        super().__init__(name)
        self.log_type = log_type

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace_id and log_type to the log record.

        Args:
            record: The log record to modify.

        Returns:
            True (always passes the record through).
        """
        record.trace_id = get_trace_id() or "-"
        record.log_type = self.log_type
        return True
