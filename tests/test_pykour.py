from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from pykour.config import Config
from pykour.pykour import Pykour
from pykour.middleware import BaseMiddleware


def test_init():
    app = Pykour()
    assert app.app is not None
    assert app._logger is not None
    assert app._config is not None
    assert app.pool is None


def test_init_with_prefix():
    app = Pykour(prefix="/api")
    assert app.prefix == "/api"


def test_init_with_config(mocker):
    config = Config()
    mocker.patch.object(config, "get_datasource_type", return_value="sqlite")
    with patch("pykour.pykour.ConnectionPool") as mock_pool:
        app = Pykour(config=config)
        assert app.config == config


def test_add_middleware(mocker):
    app = Pykour()

    class MockMiddleware(BaseMiddleware):
        def __init__(self, app, **kwargs):
            super().__init__(app)
            self.app = app
            self.kwargs = kwargs

    mocker.patch.object(app._logger, "isEnabledFor", return_value=True)
    app.add_middleware(MockMiddleware, option="value")

    assert app.app.kwargs == {"option": "value"}


@pytest.mark.asyncio
async def test_call():
    app = Pykour()

    scope = MagicMock()
    receive = MagicMock()
    send = MagicMock()
    app.app = AsyncMock()

    await app(scope, receive, send)

    app.app.assert_called_once_with(scope, receive, send)
