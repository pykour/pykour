import logging

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from pykour.middleware.uuid import UUIDMiddleware, uuid_middleware


@pytest.mark.asyncio
async def test_request_id_is_added_if_not_present():
    app = AsyncMock()
    scope = {"type": "http", "headers": []}
    receive = AsyncMock()
    send = AsyncMock()
    logger = logging.getLogger("pykour")
    middleware = UUIDMiddleware(app)

    with patch.object(logger, "isEnabledFor", return_value=True):
        await middleware(scope, receive, send)

    assert any(header[0] == b"X-Request-ID" for header in scope["headers"])
    app.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_id_is_preserved_if_present():
    app = AsyncMock()
    request_id = str(uuid4())
    scope = {"type": "http", "headers": [(b"X-Request-ID", request_id.encode("latin1"))]}
    receive = AsyncMock()
    send = AsyncMock()
    logger = logging.getLogger("pykour")
    middleware = UUIDMiddleware(app)

    with patch.object(logger, "isEnabledFor", return_value=True):
        await middleware(scope, receive, send)

    response_message = {"type": "http.response.start", "headers": []}
    middleware.scope = scope  # Ensure the scope is set in the middleware
    await middleware.send_with_request_id(response_message)

    assert scope["request_id"] == request_id
    assert any(
        header[0] == b"X-Request-ID" and header[1] == request_id.encode("latin1")
        for header in response_message["headers"]
    )
    app.assert_awaited_once()


@pytest.mark.asyncio
async def test_request_id_is_not_added_for_unsupported_type():
    app = AsyncMock()
    scope = {"type": "lifespan", "headers": []}
    receive = AsyncMock()
    send = AsyncMock()
    logger = logging.getLogger("pykour")
    middleware = UUIDMiddleware(app)

    with patch.object(logger, "isEnabledFor", return_value=True):
        await middleware(scope, receive, send)

    assert "request_id" not in scope
    app.assert_awaited_once()


def test_uuid_middleware_factory_returns_middleware():
    header_name = "x-request-id"

    async def mock_app(scope, receive, send):
        pass

    middleware = uuid_middleware(header_name)
    app = middleware(mock_app)

    assert isinstance(app, UUIDMiddleware)
    assert app.header_name == header_name
