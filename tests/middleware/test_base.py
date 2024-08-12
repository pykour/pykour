import pytest
from unittest.mock import AsyncMock

from pykour.middleware import BaseMiddleware


@pytest.mark.asyncio
async def test_call():

    class TestMiddleware(BaseMiddleware):
        async def process_request(self, scope, receive, send):
            await super().process_request(scope, receive, send)

        async def process_response(self, scope, receive, send):
            await super().process_response(scope, receive, send)

    app = AsyncMock()

    middleware = TestMiddleware(app)
    scope_mock = {}
    receive_mock = AsyncMock()
    send_mock = AsyncMock()

    await middleware(scope_mock, receive_mock, send_mock)
