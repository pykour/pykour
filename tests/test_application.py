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

    send_mock.assert_any_await(
        {
            "type": "http.response.start",
            "status": HTTPStatus.OK,
            "headers": [("Content-Type", "application/json; charset=utf-8")],
        }
    )
    send_mock.assert_any_await({"type": "http.response.body", "body": b'{"message": "Hello, world!"}'})


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

    send_mock.assert_any_await(
        {
            "type": "http.response.start",
            "status": HTTPStatus.CREATED,
            "headers": [("Content-Type", "application/json; charset=utf-8")],
        }
    )
    send_mock.assert_any_await({"type": "http.response.body", "body": b'{"status": "submitted"}'})


@pytest.mark.asyncio
async def test_404_not_found():
    app = Pykour()
    send_mock = AsyncMock()
    receive_mock = AsyncMock()
    scope = {"type": "http", "method": "GET", "path": "/nonexistent", "headers": [(b"host", b"testserver")]}

    await app(scope, receive_mock, send_mock)

    send_mock.assert_any_await(
        {
            "type": "http.response.start",
            "status": HTTPStatus.NOT_FOUND,
            "headers": [("Content-Type", "text/plain; charset=utf-8")],
        }
    )
    send_mock.assert_any_await({"type": "http.response.body", "body": b"Not Found"})


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

    send_mock.assert_any_await(
        {
            "type": "http.response.start",
            "status": HTTPStatus.METHOD_NOT_ALLOWED,
            "headers": [("Content-Type", "text/plain; charset=utf-8")],
        }
    )
    send_mock.assert_any_await({"type": "http.response.body", "body": b"Method Not Allowed"})


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

    send_mock.assert_any_await(
        {
            "type": "http.response.start",
            "status": HTTPStatus.OK,
            "headers": [("Content-Type", "application/json; charset=utf-8"), ("Allow", "OPTIONS")],
        }
    )
    send_mock.assert_any_await({"type": "http.response.body", "body": b""})


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

    assert send_mock.call_args_list[0][0][0] == {
        "type": "http.response.start",
        "status": HTTPStatus.OK,
        "headers": [("Content-Type", "application/json; charset=utf-8")],
    }

    assert send_mock.call_args_list[1][0][0] == {"type": "http.response.body", "body": b'{"message": "Hello, world!"}'}
