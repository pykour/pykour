import pytest
import json

from pykour.request import Request
from pykour.types import Message, Scope, Receive


class MockReceive:
    def __init__(self, body: bytes = b"", chunks: list[bytes] | None = None):
        self.body = body
        if chunks is not None:
            self.chunks = chunks
        elif body:
            self.chunks = [body]
        else:
            self.chunks = []
        self.index = 0

    async def __call__(self) -> Message:
        if self.index >= len(self.chunks):
            return {"type": "http.request", "body": b"", "more_body": False}

        chunk = self.chunks[self.index]
        self.index += 1
        more_body = self.index < len(self.chunks)

        return {"type": "http.request", "body": chunk, "more_body": more_body}


@pytest.fixture
def http_scope() -> Scope:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/test",
        "raw_path": b"/test",
        "root_path": "",
        "query_string": b"foo=bar&baz=qux",
        "headers": [
            (b"host", b"example.com"),
            (b"user-agent", b"test-client"),
            (b"content-type", b"application/json"),
        ],
        "server": ("localhost", 8000),
        "client": ("127.0.0.1", 56789),
    }


def test_request_basic_properties(http_scope):
    receive = MockReceive()
    req = Request(scope=http_scope, receive=receive)

    assert req.method == "GET"
    assert req.path == "/test"
    assert req.raw_path == b"/test"
    assert req.root_path == ""
    assert req.scheme == "http"
    assert req.query_string == b"foo=bar&baz=qux"
    assert req.http_version == "1.1"
    assert req.server == ("localhost", 8000)
    assert req.client == ("127.0.0.1", 56789)


def test_request_headers(http_scope):
    receive = MockReceive()
    req = Request(scope=http_scope, receive=receive)

    assert req.headers.get_first("host") == "example.com"
    assert req.headers.get_first("user-agent") == "test-client"
    assert req.headers.get_first("content-type") == "application/json"


def test_request_query_params(http_scope):
    receive = MockReceive()
    req = Request(scope=http_scope, receive=receive)

    assert req.query_params == {"foo": ["bar"], "baz": ["qux"]}


def test_request_urls(http_scope):
    receive = MockReceive()
    req = Request(scope=http_scope, receive=receive)

    assert req.url == "http://example.com/test"
    assert req.full_url == "http://example.com/test?foo=bar&baz=qux"


@pytest.mark.asyncio
async def test_request_body():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [],
    }
    body_content = b"Hello, World!"
    receive = MockReceive(body=body_content)
    req = Request(scope=scope, receive=receive)

    body = await req.body()
    assert body == body_content

    # Test that body is cached
    body2 = await req.body()
    assert body2 == body_content


@pytest.mark.asyncio
async def test_request_body_chunks():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [],
    }
    chunks = [b"Hello", b", ", b"World", b"!"]
    receive = MockReceive(chunks=chunks)
    req = Request(scope=scope, receive=receive)

    body = await req.body()
    assert body == b"Hello, World!"


@pytest.mark.asyncio
async def test_request_json():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", b"application/json")],
    }
    data = {"key": "value", "number": 42}
    body_content = json.dumps(data).encode("utf-8")
    receive = MockReceive(body=body_content)
    req = Request(scope=scope, receive=receive)

    json_data = await req.json()
    assert json_data == data


@pytest.mark.asyncio
async def test_request_form():
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
    }
    body_content = b"name=John&age=30&hobbies=reading&hobbies=coding"
    receive = MockReceive(body=body_content)
    req = Request(scope=scope, receive=receive)

    form_data = await req.form()
    assert form_data == {"name": "John", "age": "30", "hobbies": ["reading", "coding"]}


def test_request_get_method(http_scope):
    receive = MockReceive()
    req = Request(scope=http_scope, receive=receive)

    # Test getting existing properties
    assert req.get("method") == "GET"
    assert req.get("path") == "/test"

    # Test default value
    assert req.get("nonexistent", "default") == "default"
    assert req.get("nonexistent") is None
