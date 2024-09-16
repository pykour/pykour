import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from pykour.config import Config
from pykour.pykour import Pykour
from pykour.middleware import BaseMiddleware


def test_init():
    os.environ["PYKOUR_ENV"] = "development"
    app = Pykour()
    assert app.production_mode is False
    assert app.title == "Pykour"
    assert app.summary is None
    assert app.description == ""
    assert app.version == "0.1.0"

    assert app.app is not None
    assert app._config is None
    assert app.pool is None


def test_init_with_arguments():
    app = Pykour(title="Test", summary="Test Summary", description="Test Description", version="1.0.0", prefix="/api")
    assert app.title == "Test"
    assert app.summary == "Test Summary"
    assert app.description == "Test Description"
    assert app.version == "1.0.0"
    assert app.prefix == "/api"


def test_set_config_and_get_config():
    app = Pykour()
    config = MagicMock(spec=Config)
    config.get_datasource_type.return_value = "sqlite"
    config.get_datasource_pool_max_connections.return_value = 10
    config.get_datasource_db.return_value = "file::memory:"
    app.config = config
    assert app.config == config


def test_add_middleware(mocker):
    app = Pykour()

    class MockMiddleware(BaseMiddleware):
        def __init__(self, app, **kwargs):
            super().__init__(app)
            self.app = app
            self.kwargs = kwargs

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
