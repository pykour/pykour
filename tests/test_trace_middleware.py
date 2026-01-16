"""Tests for trace middleware."""

import pytest

from pykour.logging.context import get_trace_id, reset_trace_id, set_trace_id
from pykour.middleware.trace import TRACEPARENT_REGEX, TraceMiddleware


class TestTraceMiddlewareConfig:
    """Tests for trace middleware configuration."""

    def test_default_response_header(self) -> None:
        """Default response header should be X-Trace-ID."""
        middleware = TraceMiddleware(None)
        assert middleware.response_header == "X-Trace-ID"

    def test_custom_response_header(self) -> None:
        """Custom response header should be respected."""
        middleware = TraceMiddleware(None, response_header="X-Request-ID")
        assert middleware.response_header == "X-Request-ID"


class TestTraceparentParsing:
    """Tests for W3C traceparent header parsing."""

    def test_valid_traceparent(self) -> None:
        """Valid traceparent should be parsed correctly."""
        middleware = TraceMiddleware(None)
        value = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        trace_id = middleware._parse_traceparent(value)
        assert trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

    def test_traceparent_case_insensitive(self) -> None:
        """Traceparent parsing should be case insensitive."""
        middleware = TraceMiddleware(None)
        value = "00-4BF92F3577B34DA6A3CE929D0E0E4736-00F067AA0BA902B7-01"
        trace_id = middleware._parse_traceparent(value)
        assert trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

    def test_traceparent_with_whitespace(self) -> None:
        """Traceparent with whitespace should be handled."""
        middleware = TraceMiddleware(None)
        value = "  00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01  "
        trace_id = middleware._parse_traceparent(value)
        assert trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

    def test_invalid_traceparent_format(self) -> None:
        """Invalid traceparent format should return None."""
        middleware = TraceMiddleware(None)
        invalid_values = [
            "invalid",
            "00-short-00f067aa0ba902b7-01",
            "00-4bf92f3577b34da6a3ce929d0e0e4736-short-01",
            "xx-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        ]
        for value in invalid_values:
            assert middleware._parse_traceparent(value) is None

    def test_traceparent_regex(self) -> None:
        """Regex should match valid traceparent format."""
        valid = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        assert TRACEPARENT_REGEX.match(valid) is not None

        invalid = "invalid-format"
        assert TRACEPARENT_REGEX.match(invalid) is None


class TestTraceIdExtraction:
    """Tests for trace ID extraction from headers."""

    def test_extract_from_traceparent(self) -> None:
        """Should extract trace ID from traceparent header."""
        middleware = TraceMiddleware(None)
        scope = {
            "headers": [
                (
                    b"traceparent",
                    b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                ),
            ]
        }
        trace_id = middleware._extract_trace_id(scope)
        assert trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

    def test_extract_from_x_request_id(self) -> None:
        """Should extract trace ID from X-Request-ID header."""
        middleware = TraceMiddleware(None)
        scope = {
            "headers": [
                (b"x-request-id", b"custom-request-id-123"),
            ]
        }
        trace_id = middleware._extract_trace_id(scope)
        assert trace_id == "custom-request-id-123"

    def test_extract_from_x_trace_id(self) -> None:
        """Should extract trace ID from X-Trace-ID header."""
        middleware = TraceMiddleware(None)
        scope = {
            "headers": [
                (b"x-trace-id", b"custom-trace-id-456"),
            ]
        }
        trace_id = middleware._extract_trace_id(scope)
        assert trace_id == "custom-trace-id-456"

    def test_extract_from_x_correlation_id(self) -> None:
        """Should extract trace ID from X-Correlation-ID header."""
        middleware = TraceMiddleware(None)
        scope = {
            "headers": [
                (b"x-correlation-id", b"correlation-789"),
            ]
        }
        trace_id = middleware._extract_trace_id(scope)
        assert trace_id == "correlation-789"

    def test_header_priority_traceparent_wins(self) -> None:
        """traceparent should take precedence over other headers."""
        middleware = TraceMiddleware(None)
        scope = {
            "headers": [
                (b"x-request-id", b"request-id-value"),
                (
                    b"traceparent",
                    b"00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
                ),
                (b"x-trace-id", b"trace-id-value"),
            ]
        }
        trace_id = middleware._extract_trace_id(scope)
        assert trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

    def test_header_priority_x_request_id_second(self) -> None:
        """X-Request-ID should be second priority."""
        middleware = TraceMiddleware(None)
        scope = {
            "headers": [
                (b"x-trace-id", b"trace-id-value"),
                (b"x-request-id", b"request-id-value"),
                (b"x-correlation-id", b"correlation-value"),
            ]
        }
        trace_id = middleware._extract_trace_id(scope)
        assert trace_id == "request-id-value"

    def test_generate_uuid_when_no_header(self) -> None:
        """Should generate UUID when no trace header present."""
        middleware = TraceMiddleware(None)
        scope = {"headers": []}
        trace_id = middleware._extract_trace_id(scope)
        # UUID v4 hex is 32 characters
        assert len(trace_id) == 32
        assert all(c in "0123456789abcdef" for c in trace_id)

    def test_invalid_traceparent_falls_through(self) -> None:
        """Invalid traceparent should fall through to next header."""
        middleware = TraceMiddleware(None)
        scope = {
            "headers": [
                (b"traceparent", b"invalid-format"),
                (b"x-request-id", b"fallback-request-id"),
            ]
        }
        trace_id = middleware._extract_trace_id(scope)
        assert trace_id == "fallback-request-id"

    def test_empty_header_value_falls_through(self) -> None:
        """Empty header value should fall through to next header."""
        middleware = TraceMiddleware(None)
        scope = {
            "headers": [
                (b"x-request-id", b"   "),
                (b"x-trace-id", b"valid-trace-id"),
            ]
        }
        trace_id = middleware._extract_trace_id(scope)
        assert trace_id == "valid-trace-id"


class TestTraceMiddlewareIntegration:
    """Integration tests for trace middleware."""

    @pytest.mark.asyncio
    async def test_trace_id_set_in_context(self) -> None:
        """Trace ID should be available via get_trace_id() during request."""
        captured_trace_id = None

        async def app(scope, receive, send):
            nonlocal captured_trace_id
            captured_trace_id = get_trace_id()
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"OK",
                }
            )

        middleware = TraceMiddleware(app)
        scope = {
            "type": "http",
            "headers": [(b"x-request-id", b"test-trace-123")],
        }

        async def receive():
            return {"type": "http.request"}

        sent_messages = []

        async def send(message):
            sent_messages.append(message)

        await middleware(scope, receive, send)

        assert captured_trace_id == "test-trace-123"

    @pytest.mark.asyncio
    async def test_trace_id_in_response_header(self) -> None:
        """Trace ID should be added to response headers."""

        async def app(scope, receive, send):
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"text/plain")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"OK",
                }
            )

        middleware = TraceMiddleware(app)
        scope = {
            "type": "http",
            "headers": [(b"x-request-id", b"response-test-456")],
        }

        async def receive():
            return {"type": "http.request"}

        sent_messages = []

        async def send(message):
            sent_messages.append(message)

        await middleware(scope, receive, send)

        # Check response headers
        start_message = sent_messages[0]
        headers = dict(start_message["headers"])
        assert b"x-trace-id" in headers
        assert headers[b"x-trace-id"] == b"response-test-456"

    @pytest.mark.asyncio
    async def test_trace_id_in_scope(self) -> None:
        """Trace ID should be stored in scope."""
        captured_scope_trace_id = None

        async def app(scope, receive, send):
            nonlocal captured_scope_trace_id
            captured_scope_trace_id = scope.get("trace_id")
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"OK",
                }
            )

        middleware = TraceMiddleware(app)
        scope = {
            "type": "http",
            "headers": [(b"x-trace-id", b"scope-test-789")],
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            pass

        await middleware(scope, receive, send)

        assert captured_scope_trace_id == "scope-test-789"

    @pytest.mark.asyncio
    async def test_non_http_passthrough(self) -> None:
        """Non-HTTP requests should pass through without trace ID."""
        app_called = False

        async def app(scope, receive, send):
            nonlocal app_called
            app_called = True
            # Trace ID should not be set for non-HTTP
            assert get_trace_id() is None

        middleware = TraceMiddleware(app)
        scope = {
            "type": "websocket",
            "headers": [(b"x-request-id", b"should-be-ignored")],
        }

        async def receive():
            return {}

        async def send(message):
            pass

        await middleware(scope, receive, send)

        assert app_called is True

    @pytest.mark.asyncio
    async def test_trace_id_reset_after_request(self) -> None:
        """Trace ID should be reset after request completes."""
        # Set a trace ID manually first
        set_trace_id("pre-existing-id")

        async def app(scope, receive, send):
            # During request, should have new trace ID
            assert get_trace_id() == "request-trace-id"
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": b"OK",
                }
            )

        middleware = TraceMiddleware(app)
        scope = {
            "type": "http",
            "headers": [(b"x-request-id", b"request-trace-id")],
        }

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            pass

        await middleware(scope, receive, send)

        # After request, trace ID should be reset
        assert get_trace_id() is None

        # Cleanup
        reset_trace_id()


class TestLoggingContextFunctions:
    """Tests for logging context functions."""

    def test_get_set_trace_id(self) -> None:
        """get_trace_id and set_trace_id should work together."""
        reset_trace_id()  # Ensure clean state

        assert get_trace_id() is None

        set_trace_id("test-id-123")
        assert get_trace_id() == "test-id-123"

        reset_trace_id()
        assert get_trace_id() is None

    def test_generate_trace_id_format(self) -> None:
        """generate_trace_id should return valid UUID hex."""
        from pykour.logging.context import generate_trace_id

        trace_id = generate_trace_id()
        assert len(trace_id) == 32
        assert all(c in "0123456789abcdef" for c in trace_id)

        # Should generate unique IDs
        trace_id2 = generate_trace_id()
        assert trace_id != trace_id2
