import pytest

from pykour.request import Request
from pykour.types import Receive, Scope


def test_create_request():
    scope = {
        "http_version": "1.1",
        "app": "test",
        "method": "GET",
        "path": "/test",
        "query_string": b"a",
        "headers": [(b"host", b"example.com")],
    }
    request = Request(scope, None)
    assert request.version == "1.1"
    assert request.app == "test"
    assert request.method == "GET"
    assert request.query_string == b"a"
    assert request.get_header("host") == ["example.com"]
    assert request.url.scheme == "http"
    assert request.url.path == "/test"
    assert request.url.query == "a"
    assert len(request) == 6
    assert request["http_version"] == "1.1"
    for key, value in request.items():
        assert request[key] == value


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
