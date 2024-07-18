import json
import gzip
from io import BytesIO
import pytest
from pykour import Pykour
from pykour.middleware.gzip import GZipMiddleware, GZipResponder, gzip_middleware
from pykour.types import Scope, Receive, Send


@pytest.fixture
def app() -> Pykour:
    app = Pykour()
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.route("/small")
    def small_response():
        return {"message": "small response"}

    @app.route("/large")
    def large_response():
        return {"message": "large response" * 100}

    @app.route("/uncompressed")
    def uncompressed_response():
        return {"message": "uncompressed response"}

    return app


async def mock_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


@pytest.mark.asyncio
async def test_small_response(app: Pykour):
    scope = {
        "type": "http",
        "scheme": "http",
        "http_version": "1.1",
        "client": ("127.0.0.1", 50000),
        "method": "GET",
        "path": "/small",
        "headers": [(b"accept-encoding", b"gzip")],
    }

    send_messages = []

    async def mock_send(message):
        send_messages.append(message)

    await app(scope, mock_receive, mock_send)

    response_start = send_messages[0]
    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert not any(header[0] == b"content-encoding" for header in response_start["headers"])

    response_body = send_messages[1]
    assert response_body["type"] == "http.response.body"
    assert json.loads(response_body["body"]) == {"message": "small response"}


@pytest.mark.asyncio
async def test_large_response(app: Pykour):
    scope = {
        "type": "http",
        "scheme": "http",
        "http_version": "1.1",
        "client": ("127.0.0.1", 50000),
        "method": "GET",
        "path": "/large",
        "headers": [(b"accept-encoding", b"gzip")],
    }

    send_messages = []

    async def mock_send(message):
        send_messages.append(message)

    await app(scope, mock_receive, mock_send)

    response_start = send_messages[0]
    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert any(header[0] == b"content-encoding" and header[1] == b"gzip" for header in response_start["headers"])

    response_body = send_messages[1]
    assert response_body["type"] == "http.response.body"

    gzip_body = response_body["body"]
    with gzip.GzipFile(fileobj=BytesIO(gzip_body)) as f:
        decompressed_body = f.read()

    assert json.loads(decompressed_body) == {"message": "large response" * 100}


@pytest.mark.asyncio
async def test_uncompressed_response(app: Pykour):
    scope = {
        "type": "http",
        "scheme": "http",
        "http_version": "1.1",
        "client": ("127.0.0.1", 50000),
        "method": "GET",
        "path": "/uncompressed",
        "headers": [],
    }

    send_messages = []

    async def mock_send(message):
        send_messages.append(message)

    await app(scope, mock_receive, mock_send)

    response_start = send_messages[0]
    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 200
    assert not any(header[0] == b"content-encoding" for header in response_start["headers"])

    response_body = send_messages[1]
    assert response_body["type"] == "http.response.body"
    assert json.loads(response_body["body"]) == {"message": "uncompressed response"}


@pytest.mark.asyncio
async def test_non_http_request(app: Pykour):
    scope = {
        "type": "websocket",
        "path": "/ws",
    }

    send_messages = []

    async def mock_send(message):
        send_messages.append(message)

    await app(scope, mock_receive, mock_send)

    # Expect 400 Bad Request response for non-HTTP requests
    response_start = send_messages[0]
    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 400

    response_body = send_messages[1]
    assert response_body["type"] == "http.response.body"
    assert response_body["body"] == b"Bad Request"


@pytest.mark.asyncio
async def test_gzip_responder_other_message():
    async def mock_app(scope: Scope, receive: Receive, send: Send):
        await send({"type": "http.disconnect"})

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"accept-encoding", b"gzip")],
    }
    send_messages = []

    async def mock_send(message):
        send_messages.append(message)

    responder = GZipResponder(mock_app, minimum_size=1024)
    await responder(scope, mock_receive, mock_send)

    # Expect http.disconnect to be handled and passed through
    assert len(send_messages) == 1
    assert send_messages[0]["type"] == "http.disconnect"


def test_gzip_middleware_factory_returns_middleware():
    minimum_size = 1000

    async def mock_app(scope, receive, send):
        pass

    middleware = gzip_middleware(minimum_size)
    app = middleware(mock_app)

    assert isinstance(app, GZipMiddleware)
    assert app.minimum_size == minimum_size
