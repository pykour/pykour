"""Tests for pykour.request module."""

from typing import Any

from pykour.request import Request
from pykour.types import Message

from tests.conftest import create_scope


def create_receive_with_messages(body: bytes = b"") -> tuple[list[Message], Any]:
    """Create a test receive callable that returns the given body.

    This variant returns both the messages list and the receive callable,
    which is useful for tests that need to inspect the message structure.
    """
    messages: list[Message] = []
    if body:
        messages.append({"type": "http.request", "body": body, "more_body": False})
    else:
        messages.append({"type": "http.request", "body": b"", "more_body": False})

    index = 0

    async def receive() -> Message:
        nonlocal index
        if index < len(messages):
            msg = messages[index]
            index += 1
            return msg
        return {"type": "http.disconnect"}

    return messages, receive


class TestRequestProperties:
    """Test Request property accessors."""

    def test_method_default(self) -> None:
        """Default method should be GET."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.method == "GET"

    def test_method_post(self) -> None:
        """Method should reflect scope value."""
        scope = create_scope(method="POST")
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.method == "POST"

    def test_path_default(self) -> None:
        """Default path should be /."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.path == "/"

    def test_path_custom(self) -> None:
        """Path should reflect scope value."""
        scope = create_scope(path="/api/users")
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.path == "/api/users"

    def test_query_string_empty(self) -> None:
        """Empty query string by default."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.query_string == b""

    def test_query_string_with_params(self) -> None:
        """Query string should reflect scope value."""
        scope = create_scope(query_string=b"name=test&page=1")
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.query_string == b"name=test&page=1"

    def test_headers_empty(self) -> None:
        """Empty headers by default."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.headers == {}

    def test_headers_parsing(self) -> None:
        """Headers should be parsed from bytes to strings."""
        headers = [
            (b"content-type", b"application/json"),
            (b"accept", b"*/*"),
        ]
        scope = create_scope(headers=headers)
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        assert request.headers == {
            "content-type": "application/json",
            "accept": "*/*",
        }

    def test_scheme(self) -> None:
        """Scheme should reflect scope value."""
        scope = create_scope(scheme="https")
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.scheme == "https"

    def test_server(self) -> None:
        """Server should reflect scope value."""
        scope = create_scope(server=("localhost", 3000))
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.server == ("localhost", 3000)

    def test_http_version(self) -> None:
        """HTTP version should reflect scope value."""
        scope = create_scope(http_version="2")
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.http_version == "2"

    def test_scope_access(self) -> None:
        """Raw scope should be accessible."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.scope is scope


class TestRequestBody:
    """Test Request body reading."""

    async def test_body_empty(self) -> None:
        """Empty body should return empty bytes."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        body = await request.body()
        assert body == b""

    async def test_body_with_content(self) -> None:
        """Body should return received content."""
        scope = create_scope(method="POST")
        _, receive = create_receive_with_messages(body=b'{"name": "test"}')
        request = Request(scope, receive)

        body = await request.body()
        assert body == b'{"name": "test"}'

    async def test_body_cached(self) -> None:
        """Body should be cached after first read."""
        scope = create_scope(method="POST")
        _, receive = create_receive_with_messages(body=b"test data")
        request = Request(scope, receive)

        body1 = await request.body()
        body2 = await request.body()

        assert body1 == body2
        assert body1 is body2  # Same object (cached)

    async def test_body_chunked(self) -> None:
        """Body should handle chunked data."""
        scope = create_scope(method="POST")

        chunks = [
            {"type": "http.request", "body": b"chunk1", "more_body": True},
            {"type": "http.request", "body": b"chunk2", "more_body": True},
            {"type": "http.request", "body": b"chunk3", "more_body": False},
        ]
        index = 0

        async def receive() -> Message:
            nonlocal index
            if index < len(chunks):
                msg = chunks[index]
                index += 1
                return msg
            return {"type": "http.disconnect"}

        request = Request(scope, receive)
        body = await request.body()

        assert body == b"chunk1chunk2chunk3"


class TestRequestPathParams:
    """Test Request path_params property."""

    def test_path_params_default_empty(self) -> None:
        """Path params should be empty by default."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)
        assert request.path_params == {}

    def test_path_params_none_becomes_empty(self) -> None:
        """Path params None should become empty dict."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive, path_params=None)
        assert request.path_params == {}

    def test_path_params_single(self) -> None:
        """Path params should be accessible."""
        scope = create_scope(path="/api/users/123")
        _, receive = create_receive_with_messages()
        request = Request(scope, receive, path_params={"id": "123"})
        assert request.path_params == {"id": "123"}
        assert request.path_params["id"] == "123"

    def test_path_params_multiple(self) -> None:
        """Multiple path params should be accessible."""
        scope = create_scope(path="/api/users/1/posts/42")
        _, receive = create_receive_with_messages()
        request = Request(scope, receive, path_params={"userId": "1", "postId": "42"})
        assert request.path_params == {"userId": "1", "postId": "42"}
        assert request.path_params["userId"] == "1"
        assert request.path_params["postId"] == "42"


class TestRequestCookies:
    """Test Request cookies functionality."""

    def test_cookies_empty_when_no_header(self) -> None:
        """Cookies should be empty dict when no Cookie header."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        assert request.cookies == {}

    def test_cookies_single_cookie(self) -> None:
        """Single cookie should be parsed correctly."""
        scope = create_scope(headers=[(b"cookie", b"session=abc123")])
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        assert request.cookies == {"session": "abc123"}

    def test_cookies_multiple_cookies(self) -> None:
        """Multiple cookies should be parsed correctly."""
        scope = create_scope(
            headers=[(b"cookie", b"session=abc123; user=john; token=xyz")]
        )
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        assert request.cookies == {"session": "abc123", "user": "john", "token": "xyz"}

    def test_cookies_with_spaces(self) -> None:
        """Cookie values with extra spaces should be trimmed."""
        scope = create_scope(
            headers=[(b"cookie", b"  session = abc123 ;  user = john  ")]
        )
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        assert request.cookies == {"session": "abc123", "user": "john"}

    def test_cookies_lazy_evaluation(self) -> None:
        """Cookies should be lazily evaluated."""
        scope = create_scope(headers=[(b"cookie", b"a=1")])
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        # _cookies should be None initially
        assert request._cookies is None

        # Accessing cookies should populate _cookies
        _ = request.cookies
        assert request._cookies is not None
        assert request._cookies == {"a": "1"}

    def test_cookies_cached(self) -> None:
        """Cookies should be cached after first access."""
        scope = create_scope(headers=[(b"cookie", b"session=abc")])
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        cookies1 = request.cookies
        cookies2 = request.cookies

        assert cookies1 is cookies2  # Same object (cached)

    def test_get_cookie_existing(self) -> None:
        """get_cookie should return cookie value when it exists."""
        scope = create_scope(headers=[(b"cookie", b"token=xyz789")])
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        assert request.get_cookie("token") == "xyz789"

    def test_get_cookie_missing_returns_none(self) -> None:
        """get_cookie should return None for missing cookie."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        assert request.get_cookie("missing") is None

    def test_get_cookie_missing_returns_default(self) -> None:
        """get_cookie should return default for missing cookie."""
        scope = create_scope()
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        assert request.get_cookie("missing", "default_value") == "default_value"

    def test_cookies_with_equals_in_value(self) -> None:
        """Cookies with equals sign in value should be parsed correctly."""
        scope = create_scope(headers=[(b"cookie", b"token=abc=def=ghi")])
        _, receive = create_receive_with_messages()
        request = Request(scope, receive)

        # The partition method should handle this correctly
        assert request.cookies == {"token": "abc=def=ghi"}
