"""Tests for pykour.response module."""

import json
from typing import Any

from pykour.response import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
    is_body_allowed_for_status_code,
)

from tests.helpers import MockSend


async def mock_receive() -> dict[str, Any]:
    """Mock ASGI receive callable for testing."""
    return {"type": "http.request", "body": b""}


# Mock scope for testing
MOCK_SCOPE: dict[str, Any] = {
    "type": "http",
    "method": "GET",
    "path": "/",
    "headers": [],
}


class TestResponse:
    """Test base Response class."""

    async def test_default_response(self) -> None:
        """Default response should have empty body and 200 status."""
        response = Response()
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert len(send.messages) == 2
        assert send.messages[0]["type"] == "http.response.start"
        assert send.messages[0]["status"] == 200
        assert send.messages[1]["type"] == "http.response.body"
        assert send.messages[1]["body"] == b""

    async def test_response_with_bytes_content(self) -> None:
        """Response should accept bytes content."""
        response = Response(content=b"Hello")
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[1]["body"] == b"Hello"

    async def test_response_with_string_content(self) -> None:
        """Response should encode string content to bytes."""
        response = Response(content="Hello")
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[1]["body"] == b"Hello"

    async def test_response_status_code(self) -> None:
        """Response should use provided status code."""
        response = Response(status_code=404)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[0]["status"] == 404

    async def test_response_custom_headers(self) -> None:
        """Response should include custom headers."""
        response = Response(headers={"x-custom": "value"})
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"x-custom"] == b"value"

    async def test_response_content_length_header(self) -> None:
        """Response should include content-length header."""
        response = Response(content="Hello")
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"content-length"] == b"5"

    async def test_response_media_type(self) -> None:
        """Response should include content-type header when media_type is set."""
        response = Response(content="test", media_type="text/plain")
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"content-type"] == b"text/plain"


class TestJSONResponse:
    """Test JSONResponse class."""

    async def test_json_content_type(self) -> None:
        """JSONResponse should have application/json content type."""
        response = JSONResponse(content={"key": "value"})
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"content-type"] == b"application/json"

    async def test_json_dict_serialization(self) -> None:
        """JSONResponse should serialize dict to JSON."""
        data = {"name": "test", "count": 42}
        response = JSONResponse(content=data)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        body = send.messages[1]["body"]
        assert json.loads(body) == data

    async def test_json_list_serialization(self) -> None:
        """JSONResponse should serialize list to JSON."""
        data = [1, 2, 3, "four"]
        response = JSONResponse(content=data)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        body = send.messages[1]["body"]
        assert json.loads(body) == data

    async def test_json_unicode(self) -> None:
        """JSONResponse should handle unicode content."""
        data = {"message": "こんにちは"}
        response = JSONResponse(content=data)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        body = send.messages[1]["body"]
        parsed = json.loads(body)
        assert parsed["message"] == "こんにちは"

    async def test_json_null(self) -> None:
        """JSONResponse should handle None content."""
        response = JSONResponse(content=None)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        body = send.messages[1]["body"]
        assert json.loads(body) is None


class TestResponseCookies:
    """Test Response cookie functionality."""

    async def test_set_cookie_basic(self) -> None:
        """set_cookie should add Set-Cookie header."""
        response = Response(content=b"OK")
        response.set_cookie("session", "abc123")

        send = MockSend()
        await response(MOCK_SCOPE, mock_receive, send)

        headers = send.messages[0]["headers"]
        set_cookie_headers = [
            v.decode() for k, v in headers if k.lower() == b"set-cookie"
        ]

        assert len(set_cookie_headers) == 1
        assert "session=abc123" in set_cookie_headers[0]
        assert "Path=/" in set_cookie_headers[0]
        assert "SameSite=Lax" in set_cookie_headers[0]

    async def test_set_cookie_with_max_age(self) -> None:
        """set_cookie should include Max-Age when specified."""
        response = Response(content=b"OK")
        response.set_cookie("token", "xyz", max_age=3600)

        send = MockSend()
        await response(MOCK_SCOPE, mock_receive, send)

        headers = send.messages[0]["headers"]
        set_cookie_header = next(
            v.decode() for k, v in headers if k.lower() == b"set-cookie"
        )

        assert "Max-Age=3600" in set_cookie_header

    async def test_set_cookie_with_all_options(self) -> None:
        """set_cookie should support all options."""
        response = Response(content=b"OK")
        response.set_cookie(
            "token",
            "xyz",
            max_age=3600,
            expires="Thu, 01 Jan 2025 00:00:00 GMT",
            path="/api",
            domain="example.com",
            secure=True,
            httponly=True,
            samesite="Strict",
        )

        send = MockSend()
        await response(MOCK_SCOPE, mock_receive, send)

        headers = send.messages[0]["headers"]
        set_cookie_header = next(
            v.decode() for k, v in headers if k.lower() == b"set-cookie"
        )

        assert "token=xyz" in set_cookie_header
        assert "Max-Age=3600" in set_cookie_header
        assert "Expires=Thu, 01 Jan 2025 00:00:00 GMT" in set_cookie_header
        assert "Path=/api" in set_cookie_header
        assert "Domain=example.com" in set_cookie_header
        assert "Secure" in set_cookie_header
        assert "HttpOnly" in set_cookie_header
        assert "SameSite=Strict" in set_cookie_header

    async def test_set_cookie_multiple(self) -> None:
        """Multiple cookies should result in multiple Set-Cookie headers."""
        response = Response(content=b"OK")
        response.set_cookie("session", "abc")
        response.set_cookie("token", "xyz")

        send = MockSend()
        await response(MOCK_SCOPE, mock_receive, send)

        headers = send.messages[0]["headers"]
        set_cookie_headers = [
            v.decode() for k, v in headers if k.lower() == b"set-cookie"
        ]

        assert len(set_cookie_headers) == 2
        assert any("session=abc" in h for h in set_cookie_headers)
        assert any("token=xyz" in h for h in set_cookie_headers)

    async def test_delete_cookie(self) -> None:
        """delete_cookie should set expired cookie."""
        response = Response(content=b"OK")
        response.delete_cookie("session")

        send = MockSend()
        await response(MOCK_SCOPE, mock_receive, send)

        headers = send.messages[0]["headers"]
        set_cookie_header = next(
            v.decode() for k, v in headers if k.lower() == b"set-cookie"
        )

        assert "session=" in set_cookie_header
        assert "Max-Age=0" in set_cookie_header

    async def test_delete_cookie_with_domain(self) -> None:
        """delete_cookie should support domain option."""
        response = Response(content=b"OK")
        response.delete_cookie("session", domain="example.com", path="/api")

        send = MockSend()
        await response(MOCK_SCOPE, mock_receive, send)

        headers = send.messages[0]["headers"]
        set_cookie_header = next(
            v.decode() for k, v in headers if k.lower() == b"set-cookie"
        )

        assert "Domain=example.com" in set_cookie_header
        assert "Path=/api" in set_cookie_header

    def test_headers_property_includes_cookies(self) -> None:
        """headers property should include Set-Cookie headers."""
        response = Response(content=b"OK")
        response.set_cookie("session", "abc123")

        assert (
            "Set-Cookie",
            "session=abc123; Path=/; SameSite=Lax",
        ) in response.headers


class TestHTMLResponse:
    """Test HTMLResponse class."""

    async def test_html_content_type(self) -> None:
        """HTMLResponse should have text/html content type."""
        response = HTMLResponse(content="<h1>Hello</h1>")
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"content-type"] == b"text/html; charset=utf-8"

    async def test_html_default_content(self) -> None:
        """HTMLResponse should have empty default content."""
        response = HTMLResponse()
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[0]["status"] == 200
        assert send.messages[1]["body"] == b""

    async def test_html_string_content(self) -> None:
        """HTMLResponse should accept string content."""
        html = "<html><body><h1>Test</h1></body></html>"
        response = HTMLResponse(content=html)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[1]["body"] == html.encode("utf-8")

    async def test_html_bytes_content(self) -> None:
        """HTMLResponse should accept bytes content."""
        html = b"<html><body><h1>Test</h1></body></html>"
        response = HTMLResponse(content=html)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[1]["body"] == html

    async def test_html_custom_status_code(self) -> None:
        """HTMLResponse should use provided status code."""
        response = HTMLResponse(content="<p>Not Found</p>", status_code=404)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[0]["status"] == 404

    async def test_html_custom_headers(self) -> None:
        """HTMLResponse should include custom headers."""
        response = HTMLResponse(
            content="<p>Test</p>",
            headers={"x-custom": "value"},
        )
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"x-custom"] == b"value"

    async def test_html_unicode(self) -> None:
        """HTMLResponse should handle unicode content."""
        html = "<p>こんにちは</p>"
        response = HTMLResponse(content=html)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[1]["body"] == html.encode("utf-8")


class TestPlainTextResponse:
    """Test PlainTextResponse class."""

    async def test_plaintext_content_type(self) -> None:
        """PlainTextResponse should have text/plain content type."""
        response = PlainTextResponse(content="Hello, World!")
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"content-type"] == b"text/plain; charset=utf-8"

    async def test_plaintext_default_content(self) -> None:
        """PlainTextResponse should have empty default content."""
        response = PlainTextResponse()
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[0]["status"] == 200
        assert send.messages[1]["body"] == b""

    async def test_plaintext_string_content(self) -> None:
        """PlainTextResponse should accept string content."""
        text = "Hello, World!"
        response = PlainTextResponse(content=text)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[1]["body"] == text.encode("utf-8")

    async def test_plaintext_bytes_content(self) -> None:
        """PlainTextResponse should accept bytes content."""
        text = b"Hello, World!"
        response = PlainTextResponse(content=text)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[1]["body"] == text

    async def test_plaintext_custom_status_code(self) -> None:
        """PlainTextResponse should use provided status code."""
        response = PlainTextResponse(content="Error", status_code=500)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[0]["status"] == 500

    async def test_plaintext_custom_headers(self) -> None:
        """PlainTextResponse should include custom headers."""
        response = PlainTextResponse(
            content="Test",
            headers={"x-custom": "value"},
        )
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"x-custom"] == b"value"

    async def test_plaintext_unicode(self) -> None:
        """PlainTextResponse should handle unicode content."""
        text = "こんにちは"
        response = PlainTextResponse(content=text)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        assert send.messages[1]["body"] == text.encode("utf-8")


class TestIsBodyAllowedForStatusCode:
    """Test is_body_allowed_for_status_code helper function.

    Per RFC 7230/7231:
    - 1xx (Informational): No body allowed
    - 204 (No Content): No body allowed
    - 304 (Not Modified): No body allowed
    """

    def test_1xx_informational_no_body(self) -> None:
        """1xx status codes should not allow body."""
        assert is_body_allowed_for_status_code(100) is False
        assert is_body_allowed_for_status_code(101) is False
        assert is_body_allowed_for_status_code(199) is False

    def test_204_no_content_no_body(self) -> None:
        """204 No Content should not allow body."""
        assert is_body_allowed_for_status_code(204) is False

    def test_304_not_modified_no_body(self) -> None:
        """304 Not Modified should not allow body."""
        assert is_body_allowed_for_status_code(304) is False

    def test_2xx_success_allows_body(self) -> None:
        """2xx status codes (except 204) should allow body."""
        assert is_body_allowed_for_status_code(200) is True
        assert is_body_allowed_for_status_code(201) is True
        assert is_body_allowed_for_status_code(202) is True
        assert is_body_allowed_for_status_code(299) is True

    def test_3xx_redirect_allows_body(self) -> None:
        """3xx status codes (except 304) should allow body."""
        assert is_body_allowed_for_status_code(301) is True
        assert is_body_allowed_for_status_code(302) is True
        assert is_body_allowed_for_status_code(307) is True
        assert is_body_allowed_for_status_code(308) is True

    def test_4xx_client_error_allows_body(self) -> None:
        """4xx status codes should allow body."""
        assert is_body_allowed_for_status_code(400) is True
        assert is_body_allowed_for_status_code(401) is True
        assert is_body_allowed_for_status_code(404) is True
        assert is_body_allowed_for_status_code(422) is True

    def test_5xx_server_error_allows_body(self) -> None:
        """5xx status codes should allow body."""
        assert is_body_allowed_for_status_code(500) is True
        assert is_body_allowed_for_status_code(502) is True
        assert is_body_allowed_for_status_code(503) is True


class TestResponseNoBodyStatusCodes:
    """Test Response behavior for status codes that don't allow body."""

    async def test_204_no_content_type_header(self) -> None:
        """204 response should not include Content-Type header."""
        response = Response(status_code=204)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert b"content-type" not in headers

    async def test_204_no_content_length_header(self) -> None:
        """204 response should not include Content-Length header."""
        response = Response(status_code=204)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert b"content-length" not in headers

    async def test_304_no_content_type_header(self) -> None:
        """304 response should not include Content-Type header."""
        response = Response(status_code=304)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert b"content-type" not in headers

    async def test_304_no_content_length_header(self) -> None:
        """304 response should not include Content-Length header."""
        response = Response(status_code=304)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert b"content-length" not in headers

    async def test_1xx_no_content_headers(self) -> None:
        """1xx responses should not include Content-Type or Content-Length headers."""
        # Note: 1xx responses are typically handled specially by ASGI servers,
        # but we test our _build_headers logic
        response = Response(status_code=100)
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert b"content-type" not in headers
        assert b"content-length" not in headers

    async def test_204_preserves_custom_headers(self) -> None:
        """204 response should preserve custom headers (non-content)."""
        response = Response(status_code=204, headers={"x-custom": "value"})
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"x-custom"] == b"value"
        assert b"content-type" not in headers
        assert b"content-length" not in headers

    async def test_200_includes_content_headers(self) -> None:
        """200 response should include Content-Type and Content-Length headers."""
        response = Response(content="hello", status_code=200, media_type="text/plain")
        send = MockSend()

        await response(MOCK_SCOPE, mock_receive, send)

        headers = dict(send.messages[0]["headers"])
        assert headers[b"content-type"] == b"text/plain"
        assert headers[b"content-length"] == b"5"
