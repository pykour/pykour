"""Tests for Content-Type validation middleware functionality."""

from __future__ import annotations

import pytest

from pykour.middleware.content_type import ContentTypeMiddleware
from tests.helpers import (
    MockSend,
    create_noop_receive,
    create_noop_send,
    create_receive,
    create_scope,
)


class TestContentTypeMiddlewareConfig:
    """Tests for ContentTypeMiddleware configuration."""

    def test_default_config(self) -> None:
        """Default configuration should allow only application/json."""
        middleware = ContentTypeMiddleware(None)

        assert middleware.allowed_types == ["application/json"]
        assert middleware.require_content_type is True
        assert middleware.safe_methods == {"GET", "HEAD", "OPTIONS", "TRACE"}
        assert middleware.exclude_paths == []

    def test_custom_config(self) -> None:
        """Custom configuration should be respected."""
        middleware = ContentTypeMiddleware(
            None,
            allowed_types=["application/json", "text/plain"],
            require_content_type=False,
            safe_methods=["GET"],
            exclude_paths=["/upload", "/webhook"],
        )

        assert middleware.allowed_types == ["application/json", "text/plain"]
        assert middleware.require_content_type is False
        assert middleware.safe_methods == {"GET"}
        assert middleware.exclude_paths == ["/upload", "/webhook"]


class TestContentTypeMatching:
    """Tests for Content-Type matching logic."""

    def test_exact_match(self) -> None:
        """Exact content type match should work."""
        middleware = ContentTypeMiddleware(None, allowed_types=["application/json"])

        assert middleware._is_allowed("application/json") is True
        assert middleware._is_allowed("text/plain") is False

    def test_wildcard_subtype(self) -> None:
        """Wildcard subtype should match any subtype."""
        middleware = ContentTypeMiddleware(None, allowed_types=["application/*"])

        assert middleware._is_allowed("application/json") is True
        assert middleware._is_allowed("application/xml") is True
        assert middleware._is_allowed("application/octet-stream") is True
        assert middleware._is_allowed("text/plain") is False

    def test_wildcard_all(self) -> None:
        """Wildcard */* should match everything."""
        middleware = ContentTypeMiddleware(None, allowed_types=["*/*"])

        assert middleware._is_allowed("application/json") is True
        assert middleware._is_allowed("text/plain") is True
        assert middleware._is_allowed("image/png") is True

    def test_charset_parameter_ignored(self) -> None:
        """Content-Type with charset parameter should be matched correctly."""
        middleware = ContentTypeMiddleware(None, allowed_types=["application/json"])

        assert middleware._is_allowed("application/json; charset=utf-8") is True
        assert middleware._is_allowed("application/json;charset=utf-8") is True

    def test_case_insensitive(self) -> None:
        """Content-Type matching should be case insensitive."""
        middleware = ContentTypeMiddleware(None, allowed_types=["application/json"])

        assert middleware._is_allowed("Application/JSON") is True
        assert middleware._is_allowed("APPLICATION/json") is True

    def test_multiple_allowed_types(self) -> None:
        """Multiple allowed types should all work."""
        middleware = ContentTypeMiddleware(
            None,
            allowed_types=[
                "application/json",
                "application/xml",
                "text/*",
            ],
        )

        assert middleware._is_allowed("application/json") is True
        assert middleware._is_allowed("application/xml") is True
        assert middleware._is_allowed("text/plain") is True
        assert middleware._is_allowed("text/html") is True
        assert middleware._is_allowed("image/png") is False


class TestContentTypeValidation:
    """Tests for Content-Type validation during request handling."""

    @pytest.mark.asyncio
    async def test_allowed_type_passes(self) -> None:
        """Request with allowed Content-Type should pass through."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = ContentTypeMiddleware(mock_app, allowed_types=["application/json"])
        scope = create_scope(
            method="POST",
            headers=[(b"content-type", b"application/json")],
        )

        await middleware(scope, create_receive(b'{"key": "value"}'), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_disallowed_type_rejected(self) -> None:
        """Request with disallowed Content-Type should be rejected."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = ContentTypeMiddleware(mock_app, allowed_types=["application/json"])
        scope = create_scope(
            method="POST",
            headers=[(b"content-type", b"text/plain")],
        )

        await middleware(scope, create_receive(b"test"), send)

        assert send.status == 415
        body = send.json_body
        assert body["error"] == "Unsupported Media Type"
        assert "text/plain" in body["detail"]
        assert body["allowed_types"] == ["application/json"]

    @pytest.mark.asyncio
    async def test_charset_parameter_allowed(self) -> None:
        """Content-Type with charset parameter should be allowed."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = ContentTypeMiddleware(mock_app, allowed_types=["application/json"])
        scope = create_scope(
            method="POST",
            headers=[(b"content-type", b"application/json; charset=utf-8")],
        )

        await middleware(scope, create_receive(b'{"key": "value"}'), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200


class TestSafeMethodsSkip:
    """Tests for safe methods skip behavior."""

    @pytest.mark.asyncio
    async def test_get_skipped(self) -> None:
        """GET requests should skip validation."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = ContentTypeMiddleware(mock_app)
        scope = create_scope(method="GET")

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_head_skipped(self) -> None:
        """HEAD requests should skip validation."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = ContentTypeMiddleware(mock_app)
        scope = create_scope(method="HEAD")

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_options_skipped(self) -> None:
        """OPTIONS requests should skip validation."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = ContentTypeMiddleware(mock_app)
        scope = create_scope(method="OPTIONS")

        await middleware(scope, create_noop_receive(), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_post_validated(self) -> None:
        """POST requests should be validated."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = ContentTypeMiddleware(mock_app, allowed_types=["application/json"])
        scope = create_scope(
            method="POST",
            headers=[(b"content-type", b"text/plain")],
        )

        await middleware(scope, create_receive(b"test"), send)

        assert send.status == 415

    @pytest.mark.asyncio
    async def test_put_validated(self) -> None:
        """PUT requests should be validated."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = ContentTypeMiddleware(mock_app, allowed_types=["application/json"])
        scope = create_scope(
            method="PUT",
            headers=[(b"content-type", b"text/plain")],
        )

        await middleware(scope, create_receive(b"test"), send)

        assert send.status == 415

    @pytest.mark.asyncio
    async def test_patch_validated(self) -> None:
        """PATCH requests should be validated."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = ContentTypeMiddleware(mock_app, allowed_types=["application/json"])
        scope = create_scope(
            method="PATCH",
            headers=[(b"content-type", b"text/plain")],
        )

        await middleware(scope, create_receive(b"test"), send)

        assert send.status == 415

    @pytest.mark.asyncio
    async def test_delete_validated(self) -> None:
        """DELETE requests should be validated."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = ContentTypeMiddleware(mock_app, allowed_types=["application/json"])
        scope = create_scope(
            method="DELETE",
            headers=[
                (b"content-type", b"text/plain"),
                (b"content-length", b"4"),
            ],
        )

        await middleware(scope, create_receive(b"test"), send)

        assert send.status == 415


class TestPathExclusion:
    """Tests for path exclusion."""

    @pytest.mark.asyncio
    async def test_excluded_path_skipped(self) -> None:
        """Excluded paths should skip validation."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = ContentTypeMiddleware(
            mock_app,
            allowed_types=["application/json"],
            exclude_paths=["/webhook"],
        )
        scope = create_scope(
            method="POST",
            path="/webhook",
            headers=[(b"content-type", b"text/plain")],
        )

        await middleware(scope, create_receive(b"test"), mock_send)

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

        middleware = ContentTypeMiddleware(
            mock_app,
            allowed_types=["application/json"],
            exclude_paths=["/webhook"],
        )
        scope = create_scope(
            method="POST",
            path="/webhook/stripe",
            headers=[(b"content-type", b"text/plain")],
        )

        await middleware(scope, create_receive(b"test"), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_non_excluded_path_validated(self) -> None:
        """Non-excluded paths should still be validated."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = ContentTypeMiddleware(
            mock_app,
            allowed_types=["application/json"],
            exclude_paths=["/webhook"],
        )
        scope = create_scope(
            method="POST",
            path="/api/data",
            headers=[(b"content-type", b"text/plain")],
        )

        await middleware(scope, create_receive(b"test"), send)

        assert send.status == 415


class TestRequireContentType:
    """Tests for require_content_type option."""

    @pytest.mark.asyncio
    async def test_require_content_type_with_body(self) -> None:
        """Request with body but no Content-Type should be rejected when required."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = ContentTypeMiddleware(mock_app, require_content_type=True)
        scope = create_scope(
            method="POST",
            headers=[(b"content-length", b"10")],
        )

        await middleware(scope, create_receive(b"test body!"), send)

        assert send.status == 415
        body = send.json_body
        assert "required" in body["detail"]

    @pytest.mark.asyncio
    async def test_require_content_type_chunked(self) -> None:
        """Chunked request without Content-Type should be rejected when required."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = ContentTypeMiddleware(mock_app, require_content_type=True)
        scope = create_scope(
            method="POST",
            headers=[(b"transfer-encoding", b"chunked")],
        )

        await middleware(scope, create_receive(b"test"), send)

        assert send.status == 415

    @pytest.mark.asyncio
    async def test_not_require_content_type(self) -> None:
        """Request without Content-Type should pass when not required."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = ContentTypeMiddleware(mock_app, require_content_type=False)
        scope = create_scope(
            method="POST",
            headers=[(b"content-length", b"10")],
        )

        await middleware(scope, create_receive(b"test body!"), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200

    @pytest.mark.asyncio
    async def test_no_body_allowed(self) -> None:
        """Request without body should be allowed even when require_content_type is True."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = ContentTypeMiddleware(mock_app, require_content_type=True)
        scope = create_scope(
            method="POST",
            headers=[(b"content-length", b"0")],
        )

        await middleware(scope, create_receive(b""), mock_send)

        start_msg = next(m for m in messages_sent if m["type"] == "http.response.start")
        assert start_msg["status"] == 200


class TestIntegration:
    """Integration tests for ContentTypeMiddleware."""

    @pytest.mark.asyncio
    async def test_non_http_passthrough(self) -> None:
        """Non-HTTP requests should pass through."""
        called = False

        async def mock_app(scope, receive, send) -> None:
            nonlocal called
            called = True

        middleware = ContentTypeMiddleware(mock_app)
        scope = {"type": "websocket"}

        await middleware(scope, create_noop_receive(), create_noop_send())

        assert called is True

    @pytest.mark.asyncio
    async def test_error_response_format(self) -> None:
        """Error response should have proper format."""
        send = MockSend()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        middleware = ContentTypeMiddleware(mock_app, allowed_types=["application/json"])
        scope = create_scope(
            method="POST",
            headers=[(b"content-type", b"text/xml")],
        )

        await middleware(scope, create_receive(b"<test/>"), send)

        assert send.status == 415
        body = send.json_body

        assert "error" in body
        assert body["error"] == "Unsupported Media Type"
        assert "detail" in body
        assert "text/xml" in body["detail"]
        assert "allowed_types" in body
        assert body["allowed_types"] == ["application/json"]

    @pytest.mark.asyncio
    async def test_wildcard_integration(self) -> None:
        """Wildcard types should work in integration."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = ContentTypeMiddleware(
            mock_app,
            allowed_types=["application/*", "text/plain"],
        )

        # Test application/json
        scope = create_scope(
            method="POST",
            headers=[(b"content-type", b"application/json")],
        )
        await middleware(scope, create_receive(b'{"test": 1}'), mock_send)
        assert messages_sent[0]["status"] == 200

        # Test application/xml
        messages_sent.clear()
        scope = create_scope(
            method="POST",
            headers=[(b"content-type", b"application/xml")],
        )
        await middleware(scope, create_receive(b"<test/>"), mock_send)
        assert messages_sent[0]["status"] == 200

        # Test text/plain
        messages_sent.clear()
        scope = create_scope(
            method="POST",
            headers=[(b"content-type", b"text/plain")],
        )
        await middleware(scope, create_receive(b"test"), mock_send)
        assert messages_sent[0]["status"] == 200

        # Test text/html (should fail - text/* not allowed, only text/plain)
        send = MockSend()
        scope = create_scope(
            method="POST",
            headers=[(b"content-type", b"text/html")],
        )
        await middleware(scope, create_receive(b"<html/>"), send)
        assert send.status == 415
