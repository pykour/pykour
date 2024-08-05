import pytest

from pykour.request import Request
from pykour.types import Receive, Scope


@pytest.fixture
def scope() -> Scope:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"host", b"example.com"),
            (b"content-type", b"application/json; charset=utf-8"),
            (b"accept", b"application/json"),
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("example.com", 80),
        "extensions": {},
    }


@pytest.fixture
def receive() -> Receive:
    async def mock_receive() -> dict:
        return {
            "type": "http.request",
            "body": b'{"key": "value"}',
            "more_body": False,
        }

    return mock_receive


@pytest.fixture
def receive_throw_error() -> Receive:
    async def mock_receive() -> dict:
        raise Exception("error")

    return mock_receive


def test_create_request(receive: Receive):
    scope = {
        "http_version": "1.1",
        "app": "test",
        "method": "GET",
        "path": "/test",
        "query_string": b"a=1&b=1&b=2&c",
        "client": ("127.0.0.1", 12345),
        "headers": [
            (b"host", b"example.com"),
            (b"accept", b"application/json, text/plain;q=0.9, text/html;q=0.x, */*"),
        ],
    }
    request = Request(scope, receive)
    assert request.version == "1.1"
    assert request.app == "test"
    assert request.method == "GET"
    assert request.query_string == b"a=1&b=1&b=2&c"
    assert request.query_params == {"a": "1", "b": ["1", "2"]}
    assert request.get_header("host") == ["example.com"]
    assert request.url.scheme == "http"
    assert request.client == "127.0.0.1:12345"
    assert request.path == "/test"
    assert request.url.query == "a=1&b=1&b=2&c"
    assert len(request) == 7
    assert request["http_version"] == "1.1"
    for key, value in request.items():
        assert request[key] == value
    assert request.headers["host"] == ["example.com"]
    assert request.accept == ["application/json", "text/html", "*/*", "text/plain"]


def test_create_request_without_items(receive: Receive):
    scope = {}
    request = Request(scope, receive)
    assert request.method is None
    assert request.scheme is None
    assert request.version is None
    assert request.client is None
    assert request.accept == []


@pytest.mark.asyncio
async def test_body(scope: Scope, receive: Receive):
    request = Request(scope, receive)

    body = await request.body()

    assert body == b'{"key": "value"}'


@pytest.mark.asyncio
async def test_json(scope: Scope, receive: Receive):
    request = Request(scope, receive)

    json_data = await request.json()

    assert json_data == {"key": "value"}


def test_accept(scope: Scope, receive: Receive):
    request = Request(scope, receive)

    accept = request.accept

    assert accept == ["application/json"]


@pytest.mark.asyncio
async def test_json_throw_error(scope: Scope, receive_throw_error: Receive):
    request = Request(scope, receive_throw_error)

    with pytest.raises(Exception):
        request._receive = receive_throw_error
        await request.json()
