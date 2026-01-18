"""Tests for logging formatters."""

from __future__ import annotations

import json
import logging

import pytest

from pykour.logging.formatter import JsonFormatter, TextFormatter


class TestTextFormatter:
    """Tests for TextFormatter class."""

    @pytest.fixture
    def log_record(self) -> logging.LogRecord:
        """Create a basic log record for testing."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_default_format(self) -> None:
        """Default format string should be used."""
        formatter = TextFormatter()
        assert formatter._fmt == TextFormatter.DEFAULT_FORMAT

    def test_custom_format(self) -> None:
        """Custom format string should be accepted."""
        custom_fmt = "%(levelname)s - %(message)s"
        formatter = TextFormatter(fmt=custom_fmt)
        assert formatter._fmt == custom_fmt

    def test_custom_datefmt(self) -> None:
        """Custom date format should be respected."""
        custom_datefmt = "%Y-%m-%d"
        formatter = TextFormatter(datefmt=custom_datefmt)
        assert formatter.datefmt == custom_datefmt

    def test_format_with_trace_id(self, log_record: logging.LogRecord) -> None:
        """Trace ID should be included in formatted output."""
        log_record.trace_id = "abc-123"
        formatter = TextFormatter()
        formatted = formatter.format(log_record)
        assert "[abc-123]" in formatted

    def test_format_without_trace_id(self, log_record: logging.LogRecord) -> None:
        """Missing trace_id should raise ValueError."""
        formatter = TextFormatter()
        # Without trace_id, formatting should raise ValueError
        # because DEFAULT_FORMAT expects %(trace_id)s
        with pytest.raises(ValueError, match="trace_id"):
            formatter.format(log_record)

    def test_format_includes_level(self, log_record: logging.LogRecord) -> None:
        """Log level should be included in output."""
        log_record.trace_id = "test-id"
        formatter = TextFormatter()
        formatted = formatter.format(log_record)
        assert "[INFO]" in formatted

    def test_format_includes_message(self, log_record: logging.LogRecord) -> None:
        """Message should be included in output."""
        log_record.trace_id = "test-id"
        formatter = TextFormatter()
        formatted = formatter.format(log_record)
        assert "Test message" in formatted

    def test_format_includes_logger_name(self, log_record: logging.LogRecord) -> None:
        """Logger name should be included in output."""
        log_record.trace_id = "test-id"
        formatter = TextFormatter()
        formatted = formatter.format(log_record)
        assert "test.logger" in formatted


class TestJsonFormatter:
    """Tests for JsonFormatter class."""

    @pytest.fixture
    def log_record(self) -> logging.LogRecord:
        """Create a basic log record for testing."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_format_basic_record(self, log_record: logging.LogRecord) -> None:
        """Basic log record should produce valid JSON."""
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert isinstance(data, dict)

    def test_format_includes_all_fields(self, log_record: logging.LogRecord) -> None:
        """All required fields should be present."""
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert "timestamp" in data
        assert "level" in data
        assert "logger" in data
        assert "message" in data
        assert "trace_id" in data
        assert "type" in data

    def test_format_timestamp_iso8601(self, log_record: logging.LogRecord) -> None:
        """Timestamp should be ISO 8601 format."""
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        # ISO 8601 format includes 'T' separator and timezone
        timestamp = data["timestamp"]
        assert "T" in timestamp
        assert "+" in timestamp or "Z" in timestamp or timestamp.endswith("+00:00")

    def test_format_level_correct(self, log_record: logging.LogRecord) -> None:
        """Level should match log record level name."""
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert data["level"] == "INFO"

    def test_format_logger_correct(self, log_record: logging.LogRecord) -> None:
        """Logger name should match log record name."""
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert data["logger"] == "test.logger"

    def test_format_message_correct(self, log_record: logging.LogRecord) -> None:
        """Message should match log record message."""
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert data["message"] == "Test message"

    def test_format_trace_id_from_record(self, log_record: logging.LogRecord) -> None:
        """trace_id attribute should be extracted from record."""
        log_record.trace_id = "custom-trace-123"
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert data["trace_id"] == "custom-trace-123"

    def test_format_trace_id_default(self, log_record: logging.LogRecord) -> None:
        """Missing trace_id should default to '-'."""
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert data["trace_id"] == "-"

    def test_format_log_type_from_record(self, log_record: logging.LogRecord) -> None:
        """log_type attribute should be extracted from record."""
        log_record.log_type = "request"
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert data["type"] == "request"

    def test_format_log_type_default(self, log_record: logging.LogRecord) -> None:
        """Missing log_type should default to 'app'."""
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert data["type"] == "app"

    def test_format_with_exception(self) -> None:
        """Exception info should be included when present."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        formatter = JsonFormatter()
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "Test exception" in data["exception"]

    def test_format_without_exception(self, log_record: logging.LogRecord) -> None:
        """No exception field when exc_info is None."""
        formatter = JsonFormatter()
        formatted = formatter.format(log_record)
        data = json.loads(formatted)
        assert "exception" not in data

    def test_format_unicode_message(self) -> None:
        """Unicode messages should be preserved (ensure_ascii=False)."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Unicode message: \u65e5\u672c\u8a9e \u4e2d\u6587 \ud83d\ude00",
            args=(),
            exc_info=None,
        )
        formatter = JsonFormatter()
        formatted = formatter.format(record)
        # Check that Unicode is preserved (not escaped)
        assert "\u65e5\u672c\u8a9e" in formatted
        assert "\u4e2d\u6587" in formatted
        assert "\ud83d\ude00" in formatted

    @pytest.mark.parametrize(
        "level,expected",
        [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
        ],
    )
    def test_format_all_log_levels(self, level: int, expected: str) -> None:
        """All log levels should be correctly formatted."""
        record = logging.LogRecord(
            name="test.logger",
            level=level,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatter = JsonFormatter()
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["level"] == expected
