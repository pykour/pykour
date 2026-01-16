"""Tests for StreamingResponse class."""

import pytest

from pykour.response import StreamingResponse
from tests.helpers import MockSend, create_noop_receive, create_scope


class TestStreamingResponseBasic:
    """Tests for basic StreamingResponse functionality."""

    @pytest.mark.asyncio
    async def test_streaming_response_async_generator(self) -> None:
        """StreamingResponse should stream from async generator."""

        async def generate():
            for i in range(3):
                yield f"chunk{i}".encode()

        response = StreamingResponse(generate(), media_type="text/plain")
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        # Check headers
        assert send.messages[0]["type"] == "http.response.start"
        assert send.messages[0]["status"] == 200

        # Check body chunks (3 chunks + final empty)
        body_messages = [m for m in send.messages if m["type"] == "http.response.body"]
        assert len(body_messages) == 4

        # All but last should have more_body=True
        for msg in body_messages[:-1]:
            assert msg["more_body"] is True
        assert body_messages[-1]["more_body"] is False

        # Verify content
        full_body = b"".join(m["body"] for m in body_messages)
        assert full_body == b"chunk0chunk1chunk2"

    @pytest.mark.asyncio
    async def test_streaming_response_sync_iterator(self) -> None:
        """StreamingResponse should handle sync iterables."""

        def generate():
            for i in range(3):
                yield f"chunk{i}".encode()

        response = StreamingResponse(generate(), media_type="text/plain")
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        body_messages = [m for m in send.messages if m["type"] == "http.response.body"]
        full_body = b"".join(m["body"] for m in body_messages)
        assert full_body == b"chunk0chunk1chunk2"

    @pytest.mark.asyncio
    async def test_streaming_response_string_chunks(self) -> None:
        """StreamingResponse should encode string chunks."""

        async def generate():
            yield "hello "
            yield "world"

        response = StreamingResponse(generate(), media_type="text/plain")
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        body_messages = [m for m in send.messages if m["type"] == "http.response.body"]
        full_body = b"".join(m["body"] for m in body_messages)
        assert full_body == b"hello world"

    @pytest.mark.asyncio
    async def test_streaming_response_empty_generator(self) -> None:
        """StreamingResponse should handle empty generator."""

        async def generate():
            return
            yield

        response = StreamingResponse(generate(), media_type="text/plain")
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        body_messages = [m for m in send.messages if m["type"] == "http.response.body"]
        # Should have final empty body
        assert len(body_messages) == 1
        assert body_messages[0]["body"] == b""
        assert body_messages[0]["more_body"] is False

    @pytest.mark.asyncio
    async def test_streaming_response_custom_status_code(self) -> None:
        """StreamingResponse should support custom status codes."""

        async def generate():
            yield b"data"

        response = StreamingResponse(generate(), status_code=201)
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        assert send.messages[0]["status"] == 201

    @pytest.mark.asyncio
    async def test_streaming_response_custom_headers(self) -> None:
        """StreamingResponse should include custom headers."""

        async def generate():
            yield b"data"

        response = StreamingResponse(
            generate(),
            headers={"X-Custom": "value"},
            media_type="text/plain",
        )
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"X-Custom"] == b"value"
        assert headers[b"content-type"] == b"text/plain"

    @pytest.mark.asyncio
    async def test_streaming_response_no_content_length(self) -> None:
        """StreamingResponse should NOT include Content-Length header."""

        async def generate():
            yield b"data"

        response = StreamingResponse(generate(), media_type="text/plain")
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        headers = dict(send.messages[0]["headers"])
        assert b"content-length" not in headers

    @pytest.mark.asyncio
    async def test_streaming_response_list_iterator(self) -> None:
        """StreamingResponse should work with list iterator."""
        data = [b"part1", b"part2", b"part3"]

        response = StreamingResponse(iter(data), media_type="application/octet-stream")
        send = MockSend()

        await response(create_scope(), create_noop_receive(), send)

        body_messages = [m for m in send.messages if m["type"] == "http.response.body"]
        full_body = b"".join(m["body"] for m in body_messages)
        assert full_body == b"part1part2part3"


class TestStreamingResponseExport:
    """Tests for StreamingResponse exports."""

    def test_streaming_response_exported_from_pykour(self) -> None:
        """StreamingResponse should be exported from pykour package."""
        from pykour import StreamingResponse as ExportedStreamingResponse

        assert ExportedStreamingResponse is StreamingResponse
