"""Tests for request size limit middleware functionality."""

from __future__ import annotations

import pytest

from pykour.middleware.size_limit import (
    DEFAULT_MAX_SIZE,
    RequestSizeLimitMiddleware,
    RequestTooLargeError,
)
from tests.helpers import (
    MockSend,
    create_noop_receive,
    create_noop_send,
    create_receive,
    create_scope,
)


class TestRequestSizeLimitConfig:
    """Tests for RequestSizeLimitMiddleware configuration."""

    def test_default_config(self) -> None:
        """Default configuration should have 1MB limit."""
        middleware = RequestSizeLimitMiddleware(None)

        assert middleware.max_size == DEFAULT_MAX_SIZE
        assert middleware.max_size == 1 * 1024 * 1024
        assert middleware.max_size_by_content_type == {}
        assert middleware.exclude_paths == []
        assert middleware.check_content_length is True
        assert middleware.check_body_size is True

    def test_custom_config(self) -> None:
        """Custom configuration should be respected."""
        middleware = RequestSizeLimitMiddleware(
            None,
            max_size=10 * 1024 * 1024,
            max_size_by_content_type={"application/json": 1024},
            exclude_paths=["/upload", "/large"],
            check_content_length=False,
            check_body_size=False,
        )

        assert middleware.max_size == 10 * 1024 * 1024
        assert middleware.max_size_by_content_type == {"application/json": 1024}
        assert middleware.exclude_paths == ["/upload", "/large"]
        assert middleware.check_content_length is False
        assert middleware.check_body_size is False


class TestRequestTooLargeError:
    """Tests for RequestTooLargeError exception."""

    def test_error_message(self) -> None:
        """Error should include max size in message."""
        error = RequestTooLargeError(1024)

        assert error.max_size == 1024
        assert "1024" in str(error)

    def test_error_is_exception(self) -> None:
        """RequestTooLargeError should be an Exception."""
        error = RequestTooLargeError(1024)

        assert isinstance(error, Exception)


class TestRequestSizeLimitContentLength:
    """Tests for Content-Length based rejection."""

    @pytest.mark.asyncio
    async def test_rejects_large_content_length(self) -> None:
        """Request with Content-Length exceeding limit should be rejected."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = RequestSizeLimitMiddleware(mock_app, max_size=1000)
        scope = create_scope(
            method="POST",
            headers=[(b"content-length", b"2000")],
        )

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 413
        assert b"Payload Too Large" in send.body

    @pytest.mark.asyncio
    async def test_allows_small_content_length(self) -> None:
        """Request with Content-Length under limit should be allowed."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RequestSizeLimitMiddleware(mock_app, max_size=1000)
        scope = create_scope(
            method="POST",
            headers=[(b"content-length", b"500")],
        )

        await middleware(scope, create_receive(b"x" * 500), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_no_content_length_allowed(self) -> None:
        """Request without Content-Length should be allowed (checked during body read)."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RequestSizeLimitMiddleware(mock_app, max_size=1000)
        scope = create_scope(method="POST")

        await middleware(scope, create_receive(b"small body"), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_content_length_check_disabled(self) -> None:
        """Should skip Content-Length check when disabled."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RequestSizeLimitMiddleware(
            mock_app,
            max_size=1000,
            check_content_length=False,
            check_body_size=False,
        )
        scope = create_scope(
            method="POST",
            headers=[(b"content-length", b"2000")],
        )

        await middleware(scope, create_receive(b"x" * 500), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200


class TestRequestSizeLimitContentType:
    """Tests for Content-Type specific limits."""

    def test_get_max_size_default(self) -> None:
        """Should return default max size when no content type match."""
        middleware = RequestSizeLimitMiddleware(None, max_size=1000)
        scope = create_scope()

        assert middleware._get_max_size(scope) == 1000

    def test_get_max_size_by_content_type(self) -> None:
        """Should return content-type specific limit."""
        middleware = RequestSizeLimitMiddleware(
            None,
            max_size=1000,
            max_size_by_content_type={
                "application/json": 500,
                "multipart/form-data": 10000,
            },
        )

        json_scope = create_scope(headers=[(b"content-type", b"application/json")])
        assert middleware._get_max_size(json_scope) == 500

        multipart_scope = create_scope(
            headers=[(b"content-type", b"multipart/form-data; boundary=---")]
        )
        assert middleware._get_max_size(multipart_scope) == 10000

    def test_get_max_size_unknown_type_uses_default(self) -> None:
        """Should use default for unknown content types."""
        middleware = RequestSizeLimitMiddleware(
            None,
            max_size=1000,
            max_size_by_content_type={"application/json": 500},
        )

        scope = create_scope(headers=[(b"content-type", b"text/plain")])
        assert middleware._get_max_size(scope) == 1000


class TestRequestSizeLimitExclusion:
    """Tests for path exclusion."""

    @pytest.mark.asyncio
    async def test_excluded_path_skipped(self) -> None:
        """Excluded paths should skip size checking."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RequestSizeLimitMiddleware(
            mock_app,
            max_size=100,
            exclude_paths=["/upload"],
        )
        scope = create_scope(
            method="POST",
            path="/upload",
            headers=[(b"content-length", b"10000")],
        )

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_excluded_path_prefix(self) -> None:
        """Path prefix exclusion should work."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RequestSizeLimitMiddleware(
            mock_app,
            max_size=100,
            exclude_paths=["/upload"],
        )
        scope = create_scope(
            method="POST",
            path="/upload/files",
            headers=[(b"content-length", b"10000")],
        )

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_non_excluded_path_checked(self) -> None:
        """Non-excluded paths should still be checked."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = RequestSizeLimitMiddleware(
            mock_app,
            max_size=100,
            exclude_paths=["/upload"],
        )
        scope = create_scope(
            method="POST",
            path="/api/data",
            headers=[(b"content-length", b"200")],
        )

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 413


class TestRequestSizeLimitBodyStreaming:
    """Tests for body size checking during streaming."""

    @pytest.mark.asyncio
    async def test_body_size_check_during_streaming(self) -> None:
        """Should check body size during streaming."""

        async def mock_app(scope, receive, send):
            # Read body which triggers size check
            chunks = []
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    break
                body = message.get("body", b"")
                if body:
                    chunks.append(body)
                if not message.get("more_body", False):
                    break

            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        send = MockSend()
        middleware = RequestSizeLimitMiddleware(
            mock_app,
            max_size=100,
            check_content_length=False,  # Only check body size
        )

        # Create chunked receive that exceeds limit
        chunks = [
            {"type": "http.request", "body": b"x" * 60, "more_body": True},
            {
                "type": "http.request",
                "body": b"x" * 60,
                "more_body": False,
            },  # Total 120 > 100
        ]
        index = 0

        async def chunked_receive():
            nonlocal index
            if index < len(chunks):
                msg = chunks[index]
                index += 1
                return msg
            return {"type": "http.disconnect"}

        scope = create_scope(method="POST")

        await middleware(scope, chunked_receive, send)

        assert send.status == 413

    @pytest.mark.asyncio
    async def test_body_size_under_limit_allowed(self) -> None:
        """Body under limit should be allowed."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            # Read body
            await receive()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RequestSizeLimitMiddleware(mock_app, max_size=100)
        scope = create_scope(method="POST")

        await middleware(scope, create_receive(b"x" * 50), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200


class TestRequestSizeLimitIntegration:
    """Integration tests for RequestSizeLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_non_http_passthrough(self) -> None:
        """Non-HTTP requests should pass through."""
        called = False

        async def mock_app(scope, receive, send) -> None:
            nonlocal called
            called = True

        middleware = RequestSizeLimitMiddleware(mock_app)
        scope = {"type": "websocket"}

        await middleware(scope, create_noop_receive(), create_noop_send())

        assert called is True

    @pytest.mark.asyncio
    async def test_get_request_no_body_allowed(self) -> None:
        """GET request should be allowed even without body."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RequestSizeLimitMiddleware(mock_app, max_size=100)
        scope = create_scope(method="GET")

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_error_response_format(self) -> None:
        """Error response should include proper format."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = RequestSizeLimitMiddleware(mock_app, max_size=100)
        scope = create_scope(
            method="POST",
            headers=[(b"content-length", b"200")],
        )

        await middleware(scope, create_noop_receive(), send)

        assert send.status == 413
        body = send.json_body

        assert "error" in body
        assert body["error"] == "Payload Too Large"
        assert "detail" in body
        assert "max_size" in body
        assert body["max_size"] == 100
