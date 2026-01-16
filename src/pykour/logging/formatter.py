"""Log formatters for text and JSON output.

This module provides formatters for structured logging output,
supporting both human-readable text and machine-parseable JSON formats.

Example:
    import logging
    from pykour.logging import JsonFormatter, TextFormatter, TraceLogFilter

    # JSON format (for production/log aggregation)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceLogFilter())

    # Text format (for development)
    handler = logging.StreamHandler()
    handler.setFormatter(TextFormatter())
    handler.addFilter(TraceLogFilter())
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class TextFormatter(logging.Formatter):
    """Human-readable text format log output.

    Output format:
        2025-01-13 10:30:00 [INFO] [abc-123] myapp: User created

    The format includes timestamp, level, trace_id, logger name, and message.

    Example:
        handler = logging.StreamHandler()
        handler.setFormatter(TextFormatter())
        handler.addFilter(TraceLogFilter())
        logger.addHandler(handler)

    Attributes:
        DEFAULT_FORMAT: The default format string used.
    """

    DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] [%(trace_id)s] %(name)s: %(message)s"

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
    ) -> None:
        """Initialize the text formatter.

        Args:
            fmt: Custom format string. Defaults to DEFAULT_FORMAT.
            datefmt: Custom date format string.
        """
        super().__init__(fmt or self.DEFAULT_FORMAT, datefmt)


class JsonFormatter(logging.Formatter):
    """JSON format log output for structured logging.

    Output format (single line):
        {"timestamp": "...", "level": "INFO", "trace_id": "...", ...}

    Fields included:
        - timestamp: ISO 8601 format in UTC
        - level: Log level name
        - logger: Logger name
        - message: Log message
        - trace_id: Request trace ID (or "-" if not in request context)
        - type: Log type ("app" by default, set by TraceLogFilter)
        - exception: Exception info (if present)

    Example:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler.addFilter(TraceLogFilter())
        logger.addHandler(handler)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON string representation of the log record.
        """
        log_data: dict[str, str | int | float | None] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
            "type": getattr(record, "log_type", "app"),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)
