"""Tests for EventSourceResponse (SSE) class."""

import pytest

from pykour.response import EventSourceResponse, ServerSentEvent
from tests.helpers import MockSend, create_noop_receive, create_scope


class TestServerSentEvent:
    """Tests for ServerSentEvent encoding."""

    def test_simple_data_event(self) -> None:
        """SSE event with just data."""
        event = ServerSentEvent(data="hello")
        encoded = event.encode()
        assert encoded == b"data: hello\n\n"

    def test_event_with_type(self) -> None:
        """SSE event with event type."""
        event = ServerSentEvent(data="hello", event="message")
        encoded = event.encode()
        assert b"event: message\n" in encoded
        assert b"data: hello\n" in encoded

    def test_event_with_id(self) -> None:
        """SSE event with ID."""
        event = ServerSentEvent(data="hello", id="123")
        encoded = event.encode()
        assert b"id: 123\n" in encoded

    def test_event_with_retry(self) -> None:
        """SSE event with retry interval."""
        event = ServerSentEvent(data="hello", retry=5000)
        encoded = event.encode()
        assert b"retry: 5000\n" in encoded

    def test_json_data(self) -> None:
        """SSE event with JSON data."""
        event = ServerSentEvent(data={"count": 1})
        encoded = event.encode()
        # JSON format: {"count":1}
        assert b"data: {" in encoded
        assert b'"count"' in encoded

    def test_multiline_data(self) -> None:
        """SSE event with multiline data."""
        event = ServerSentEvent(data="line1\nline2")
        encoded = event.encode()
        assert encoded == b"data: line1\ndata: line2\n\n"

    def test_full_event(self) -> None:
        """SSE event with all fields."""
        event = ServerSentEvent(
            data="payload",
            event="update",
            id="msg-1",
            retry=3000,
        )
        encoded = event.encode()
        assert b"event: update\n" in encoded
        assert b"id: msg-1\n" in encoded
        assert b"retry: 3000\n" in encoded
        assert b"data: payload\n" in encoded
        assert encoded.endswith(b"\n\n")


class TestEventSourceResponse:
    """Tests for EventSourceResponse."""

    @pytest.mark.asyncio
    async def test_sse_response_headers(self) -> None:
        """EventSourceResponse should set correct headers."""

        async def generate():
            yield ServerSentEvent(data="test")

        response = EventSourceResponse(generate())
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"content-type"] == b"text/event-stream"
        assert headers[b"cache-control"] == b"no-cache"
        assert headers[b"connection"] == b"keep-alive"

    @pytest.mark.asyncio
    async def test_sse_response_string_events(self) -> None:
        """EventSourceResponse should handle string events."""

        async def generate():
            yield "first"
            yield "second"

        response = EventSourceResponse(generate())
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        body_messages = [m for m in send.messages if m["type"] == "http.response.body"]
        full_body = b"".join(m["body"] for m in body_messages)

        assert b"data: first\n\n" in full_body
        assert b"data: second\n\n" in full_body

    @pytest.mark.asyncio
    async def test_sse_response_dict_events(self) -> None:
        """EventSourceResponse should JSON-encode dict events."""

        async def generate():
            yield {"status": "ok"}

        response = EventSourceResponse(generate())
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        body_messages = [m for m in send.messages if m["type"] == "http.response.body"]
        full_body = b"".join(m["body"] for m in body_messages)

        assert b"data: {" in full_body
        assert b'"status"' in full_body

    @pytest.mark.asyncio
    async def test_sse_response_server_sent_events(self) -> None:
        """EventSourceResponse should handle ServerSentEvent objects."""

        async def generate():
            yield ServerSentEvent(data="hello", event="greeting", id="1")
            yield ServerSentEvent(data={"count": 42}, event="update")

        response = EventSourceResponse(generate())
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        body_messages = [m for m in send.messages if m["type"] == "http.response.body"]
        full_body = b"".join(m["body"] for m in body_messages)

        # First event
        assert b"event: greeting\n" in full_body
        assert b"id: 1\n" in full_body
        assert b"data: hello\n" in full_body

        # Second event
        assert b"event: update\n" in full_body

    @pytest.mark.asyncio
    async def test_sse_response_streaming_chunks(self) -> None:
        """EventSourceResponse should stream each event as a separate chunk."""

        async def generate():
            yield "event1"
            yield "event2"

        response = EventSourceResponse(generate())
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        body_messages = [m for m in send.messages if m["type"] == "http.response.body"]

        # 2 events + final empty body = 3 messages
        assert len(body_messages) == 3

        # First two have more_body=True
        assert body_messages[0]["more_body"] is True
        assert body_messages[1]["more_body"] is True
        # Last has more_body=False
        assert body_messages[2]["more_body"] is False

    @pytest.mark.asyncio
    async def test_sse_response_custom_status_code(self) -> None:
        """EventSourceResponse should support custom status codes."""

        async def generate():
            yield "data"

        response = EventSourceResponse(generate(), status_code=202)
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        assert send.messages[0]["status"] == 202

    @pytest.mark.asyncio
    async def test_sse_response_custom_headers(self) -> None:
        """EventSourceResponse should include custom headers."""

        async def generate():
            yield "data"

        response = EventSourceResponse(
            generate(),
            headers={"X-Custom": "header-value"},
        )
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"X-Custom"] == b"header-value"

    @pytest.mark.asyncio
    async def test_sse_response_no_content_length(self) -> None:
        """EventSourceResponse should NOT include Content-Length header."""

        async def generate():
            yield "data"

        response = EventSourceResponse(generate())
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        headers = dict(send.messages[0]["headers"])
        assert b"content-length" not in headers


class TestSSEExport:
    """Tests for SSE exports."""

    def test_event_source_response_exported_from_pykour(self) -> None:
        """EventSourceResponse should be exported from pykour package."""
        from pykour import EventSourceResponse as ExportedEventSourceResponse

        assert ExportedEventSourceResponse is EventSourceResponse

    def test_server_sent_event_exported_from_pykour(self) -> None:
        """ServerSentEvent should be exported from pykour package."""
        from pykour import ServerSentEvent as ExportedServerSentEvent

        assert ExportedServerSentEvent is ServerSentEvent
