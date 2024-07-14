from http import HTTPStatus
from unittest.mock import AsyncMock

import pytest

from pykour import Pykour, Request, Response
from pykour.middleware import BaseMiddleware


@pytest.mark.asyncio
async def test_get_route():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "GET", "path": "/test", "headers": [(b"host", b"testserver")]}

    @app.get("/test")
    async def test_handler(request: Request, response: Response):
        return {"message": "Hello, world!"}

    await app(scope, receive_mock, send_mock)

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.OK
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"

    assert second_call_args == {"type": "http.response.body", "body": b'{"message": "Hello, world!"}'}


@pytest.mark.asyncio
async def test_post_route():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "POST", "path": "/submit", "headers": [(b"host", b"testserver")]}

    @app.post("/submit")
    async def submit_handler(request: Request, response: Response):
        return {"status": "submitted"}

    await app(scope, receive_mock, send_mock)

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.CREATED
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"

    assert second_call_args == {"type": "http.response.body", "body": b'{"status": "submitted"}'}


@pytest.mark.asyncio
async def test_put_route():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "PUT", "path": "/test", "headers": [(b"host", b"testserver")]}

    @app.put("/test")
    async def test_handler(request: Request, response: Response):
        return {"message": "Hello, world!"}

    await app(scope, receive_mock, send_mock)

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.OK
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"

    assert second_call_args == {"type": "http.response.body", "body": b'{"message": "Hello, world!"}'}


@pytest.mark.asyncio
async def test_delete_route():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "DELETE", "path": "/test", "headers": [(b"host", b"testserver")]}

    @app.delete("/test")
    async def test_handler(request: Request, response: Response): ...

    await app(scope, receive_mock, send_mock)

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.NO_CONTENT
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"

    assert second_call_args == {"type": "http.response.body", "body": b""}


@pytest.mark.asyncio
async def test_patch_route():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "PATCH", "path": "/test", "headers": [(b"host", b"testserver")]}

    @app.patch("/test")
    async def test_handler(request: Request, response: Response):
        return {"message": "Hello, world!"}

    await app(scope, receive_mock, send_mock)

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.OK
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"

    assert second_call_args == {"type": "http.response.body", "body": b'{"message": "Hello, world!"}'}


@pytest.mark.asyncio
async def test_head_route():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "HEAD", "path": "/test", "headers": [(b"host", b"testserver")]}

    @app.head("/test")
    async def test_handler(request: Request, response: Response):
        return {"message": "Hello, world!"}

    await app(scope, receive_mock, send_mock)

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.OK
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"
        elif header[0] == b"Content-Length":
            assert header[1] == b"24"

    assert second_call_args == {"type": "http.response.body", "body": b""}


@pytest.mark.asyncio
async def test_404_not_found():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "GET", "path": "/nonexistent", "headers": [(b"host", b"testserver")]}

    await app(scope, receive_mock, send_mock)

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.NOT_FOUND
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"

    assert second_call_args == {"type": "http.response.body", "body": b"Not Found"}


@pytest.mark.asyncio
async def test_method_not_allowed():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "POST", "path": "/onlyget", "headers": [(b"host", b"testserver")]}

    @app.get("/onlyget")
    async def only_get_handler(request: Request, response: Response):
        return {"message": "This is GET"}

    await app(scope, receive_mock, send_mock)

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.METHOD_NOT_ALLOWED
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"

    assert second_call_args == {"type": "http.response.body", "body": b"Method Not Allowed"}


@pytest.mark.asyncio
async def test_options_method():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "OPTIONS", "path": "/options", "headers": [(b"host", b"testserver")]}

    @app.options("/options")
    async def options_handler(request: Request, response: Response):
        return {"message": "This is OPTIONS"}

    await app(scope, receive_mock, send_mock)

    assert send_mock.call_count == 2

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.OK
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"
        elif header[0] == b"Allow":
            assert header[1] == b"OPTIONS"

    assert second_call_args == {"type": "http.response.body", "body": b""}


@pytest.mark.asyncio
async def test_add_middleware():
    app = Pykour()

    class TestMiddleware(BaseMiddleware):
        async def process_request(self, scope, receive, send):
            await super().process_request(scope, receive, send)

        async def process_response(self, scope, receive, send):
            await super().process_response(scope, receive, send)

    app.add_middleware(TestMiddleware)

    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    dummy_scope = {"type": "http", "method": "GET", "path": "/test", "headers": [(b"host", b"testserver")]}

    @app.get("/test")
    async def test_handler(request: Request, response: Response):
        return {"message": "Hello, world!"}

    await app(dummy_scope, receive_mock, send_mock)

    assert send_mock.call_count == 2

    first_call_args = send_mock.call_args_list[0][0][0]
    second_call_args = send_mock.call_args_list[1][0][0]
    assert first_call_args["type"] == "http.response.start"
    assert first_call_args["status"] == HTTPStatus.OK
    for header in first_call_args["headers"]:
        if header[0] == b"Content-Type":
            assert header[1] == b"application/json; charset=utf-8"

    assert second_call_args == {"type": "http.response.body", "body": b'{"message": "Hello, world!"}'}


@pytest.mark.asyncio
def test_get_config():
    app = Pykour()
    app._config = {"key": "value"}
    assert app.config == {"key": "value"}


@pytest.mark.asyncio
async def test_request_unsuported_method():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "TRACE", "path": "/test", "headers": [(b"host", b"testserver")]}

    @app.get("/test")
    async def test_handler(request: Request, response: Response):
        return {"message": "Hello, world!"}

    await app(scope, receive_mock, send_mock)
    assert send_mock.call_count == 2
    assert send_mock.call_args_list[0][0][0]["status"] == HTTPStatus.NOT_FOUND
    assert send_mock.call_args_list[1][0][0]["body"] == b"Not Found"


@pytest.mark.asyncio
async def test_set_unsupported_method():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "TRACE", "path": "/test", "headers": [(b"host", b"testserver")]}

    with pytest.raises(ValueError):

        @app.route("/test", method="TRACE")
        async def trace_handler(request: Request, response: Response):
            return {"message": "This is TRACE"}
