from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from pykour.config import Config
from pykour.exceptions import ResourceNotFoundException
from pykour.pykour import Pykour
from pykour.middleware import BaseMiddleware
from pykour.testing import perform, get, scope, post


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


@pytest.mark.asyncio
async def test_a():
    from pykour import Pykour, Router

    app = Pykour()

    user_router = Router()

    @user_router.get("/")
    async def get_users():
        return "Get users"

    @user_router.get("/{user_id}")
    async def get_user(user_id: int):
        return f"Get user {user_id}"

    api_router = Router("/api")
    api_router.add_router(user_router, prefix="/users")

    app.add_router(api_router)

    @app.route("/")
    async def home():
        return "Hello, World!"

    @app.route("/exception1")
    async def home():
        raise Exception("Exception 1")

    @app.route("/exception2")
    async def home():
        raise ResourceNotFoundException("Exception 2")

    response = await perform(app, get("/"))
    response.is_ok().expect("Hello, World!")
    response = await perform(app, post("/", body="Hello, World!"))
    response.is_method_not_allowed().expect("Method Not Allowed")
    response = await perform(app, get("/api/users"))
    response.is_ok().expect("Get users")
    response = await perform(app, get("/api/users/1"))
    response.is_ok().expect("Get user 1")
    response = await perform(app, scope("/", scheme="ws"))
    response.is_bad_request().expect("Bad Request")
    response = await perform(app, scope("/", method="TRACE"))
    response.is_not_found().expect("Not Found")
    response = await perform(app, get("/notfound"))
    response.is_not_found().expect("Not Found")
    response = await perform(app, get("/exception1"))
    response.is_server_error().expect("Internal Server Error")
    response = await perform(app, get("/exception2"))
    response.is_not_found().expect("Exception 2")
