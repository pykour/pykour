import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from pykour.middleware.requestid import RequestIDMiddleware


@pytest.mark.asyncio
async def test_request_id_is_added_if_not_present():
    app_mock = AsyncMock()
    middleware = RequestIDMiddleware(app_mock)
    scope = {"type": "http", "headers": []}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    assert any(header[0] == b"x-request-id" for header in scope["headers"])
    app_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_id_is_preserved_if_present():
    app_mock = AsyncMock()
    middleware = RequestIDMiddleware(app_mock)
    request_id = str(uuid4())
    scope = {"type": "http", "headers": [(b"x-request-id", request_id.encode("latin1"))]}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    response_message = {"type": "http.response.start", "headers": []}
    middleware.scope = scope  # Ensure the scope is set in the middleware
    await middleware.send_with_request_id(response_message)

    assert scope["request_id"] == request_id
    assert any(
        header[0] == b"X-Request-ID" and header[1] == request_id.encode("latin1")
        for header in response_message["headers"]
    )
    app_mock.assert_awaited_once()


@pytest.mark.asyncio
async def request_id_is_added_to_response_headers():
    app_mock = AsyncMock()
    middleware = RequestIDMiddleware(app_mock)
    scope = {"type": "http", "headers": []}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    response_message = {"type": "http.response.start", "headers": []}
    await middleware.send_with_request_id(response_message)

    assert any(header[0] == b"x-request-id" for header in response_message["headers"])


@pytest.mark.asyncio
async def test_request_id_is_not_added_for_lifespan_scope():
    app_mock = AsyncMock()
    middleware = RequestIDMiddleware(app_mock)
    scope = {"type": "lifespan", "headers": []}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    assert "request_id" not in scope
    app_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_id_is_not_added_for_lifespan_scope():
    app_mock = AsyncMock()
    middleware = RequestIDMiddleware(app_mock)
    scope = {"type": "lifespan", "headers": []}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    assert "request_id" not in scope
    app_mock.assert_awaited_once()
