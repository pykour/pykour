import pytest

from pykour.callable import AppCallable
from pykour.types import Receive, Scope, Send


class MockApp:
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        self.scope = scope
        self.receive = receive
        self.send = send


class MockMiddleware1:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        self.scope = scope
        self.receive = receive
        self.send = send


class MockMiddleware2:

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        self.scope = scope
        self.receive = receive
        self.send = send


@pytest.fixture
def scope():
    return {}


@pytest.fixture
def receive():
    async def receive():
        return None

    return receive


@pytest.fixture
def send():
    async def send(x):
        return None

    return send


@pytest.fixture
def app():
    return MockApp()


@pytest.mark.it("should initialize the app")
def test_init():
    callable = AppCallable()
    assert callable._app is None
    assert callable._base_app is None
    assert callable._middlewares == []


@pytest.mark.it("should set and get the app")
def test_set_get_app():
    callable = AppCallable()
    app = MockApp()
    callable.app = app
    assert callable.app == app


@pytest.mark.it("should call the app with the scope, receive and send")
@pytest.mark.asyncio
async def test_call(app, scope, receive, send):
    callable = AppCallable()
    callable.app = app

    await callable(scope, receive, send)
    assert "app" in scope
    assert callable.app.scope == scope
    assert callable.app.receive == receive
    assert callable.app.send == send


@pytest.mark.it("should add middlewares, build the app and call it")
@pytest.mark.asyncio
async def test_add_middleware(app, scope, receive, send):
    callable = AppCallable()

    callable.app = app
    callable.add_middleware(MockMiddleware1)
    callable.add_middleware(MockMiddleware2)

    await callable(scope, receive, send)

    assert type(callable._app) is MockMiddleware2
    assert type(callable._app.app) is MockMiddleware1
    assert type(callable._app.app.app) is MockApp
