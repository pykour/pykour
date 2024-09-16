from unittest.mock import MagicMock

import pytest


def test_is_supported_schema():
    from pykour.internal.handler.request import is_supported_scheme
    from pykour.request import Request

    request = MagicMock(spec=Request)

    request.scheme = "HTTP"
    assert is_supported_scheme(request) is True

    request.scheme = "HTTPS"
    assert is_supported_scheme(request) is False


def test_is_supported_method():
    from pykour.internal.handler.request import is_supported_method
    from pykour.request import Request

    request = MagicMock(spec=Request)

    request.method = "GET"
    assert is_supported_method(request) is True

    request.method = "POST"
    assert is_supported_method(request) is True

    request.method = "PUT"
    assert is_supported_method(request) is True

    request.method = "DELETE"
    assert is_supported_method(request) is True

    request.method = "PATCH"
    assert is_supported_method(request) is True

    request.method = "OPTIONS"
    assert is_supported_method(request) is True

    request.method = "HEAD"
    assert is_supported_method(request) is True

    request.method = "TRACE"
    assert is_supported_method(request) is False


def test_is_method_allowed():
    from pykour.internal.handler.request import is_method_allowed
    from pykour.request import Request

    request = MagicMock(spec=Request)

    request.app.get_allowed_methods.return_value = []
    assert is_method_allowed(request) is True

    request.app.get_allowed_methods.return_value = ["GET", "POST"]

    request.method = "GET"
    assert is_method_allowed(request) is True

    request.method = "POST"
    assert is_method_allowed(request) is True

    request.method = "PUT"
    assert is_method_allowed(request) is False


def test_is_valid_route():
    from pykour.internal.handler.request import is_valid_route
    from pykour.request import Request

    request = MagicMock(spec=Request)

    request.app.exists.return_value = True
    assert is_valid_route(request) is True

    request.app.exists.return_value = False
    assert is_valid_route(request) is False


@pytest.mark.asyncio
async def test_bind_args1():
    from pykour.internal.handler.request import bind_args
    from pykour.request import Request
    from pykour.response import Response
    from pykour.schema import BaseSchema
    from pykour.config import Config
    from pykour.db.connection import Connection
    from typing import Dict, Any
    import inspect

    class UserSchema(BaseSchema):
        name: str
        age: int

    config = MagicMock()
    conn = MagicMock()
    pool = MagicMock()
    pool.get_connection.return_value = conn
    app = MagicMock()
    app.config = config
    app.pool = pool
    request = MagicMock(spec=Request)
    request.path_params = {"value1": "1"}
    request.app = app
    request.json.return_value = {"name": "John", "age": 30}
    response = MagicMock(spec=Response)
    items = MagicMock()

    items.__iter__.return_value = [
        ("user", inspect.Parameter("user", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=UserSchema)),
        ("body1", inspect.Parameter("body1", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=dict)),
        ("body2", inspect.Parameter("body2", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Dict)),
        ("r1", inspect.Parameter("r1", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Request)),
        ("req", inspect.Parameter("req", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
        ("request", inspect.Parameter("request", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
        ("r2", inspect.Parameter("r2", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Response)),
        ("res", inspect.Parameter("res", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
        ("resp", inspect.Parameter("resp", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
        ("response", inspect.Parameter("response", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
        ("value1", inspect.Parameter("value1", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=int)),
        ("c1", inspect.Parameter("c1", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Config)),
        ("config", inspect.Parameter("config", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
        ("con1", inspect.Parameter("conn", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Connection)),
        ("conn", inspect.Parameter("conn", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
        ("connection", inspect.Parameter("conn", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
    ]

    bound_args, c = await bind_args(request, response, items)

    assert bound_args["user"].name == "John"
    assert bound_args["user"].age == 30
    assert bound_args["body1"] == {"name": "John", "age": 30}
    assert bound_args["body2"] == {"name": "John", "age": 30}
    assert bound_args["r1"] == request
    assert bound_args["req"] == request
    assert bound_args["request"] == request
    assert bound_args["r2"] == response
    assert bound_args["res"] == response
    assert bound_args["resp"] == response
    assert bound_args["response"] == response
    assert bound_args["value1"] == 1
    assert bound_args["c1"] == config
    assert bound_args["config"] == config
    assert bound_args["con1"] == conn
    assert bound_args["conn"] == conn
    assert bound_args["connection"] == conn
    assert c == conn


@pytest.mark.asyncio
async def test_bind_args2():
    from pykour.internal.handler.request import bind_args
    from pykour.request import Request
    from pykour.response import Response
    from typing import Any
    import inspect

    app = MagicMock()
    app.pool = None
    request = MagicMock(spec=Request)
    request.path_params = {}
    request.app = app
    response = MagicMock(spec=Response)
    items = MagicMock()

    items.__iter__.return_value = [
        ("dummy", inspect.Parameter("dummy", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
        ("conn", inspect.Parameter("conn", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Any)),
    ]

    bound_args, c = await bind_args(request, response, items)

    assert bound_args["dummy"] is None
    assert bound_args["conn"] is None
    assert c is None


@pytest.mark.asyncio
async def test_call_sync(mocker):
    from pykour.internal.handler.request import call

    def func():
        return "1"

    request = MagicMock()
    response = MagicMock()

    mocker.patch("pykour.internal.handler.request.bind_args", return_value=({}, None))
    result = await call(func, request, response)

    assert result == "1"


@pytest.mark.asyncio
async def test_call_async(mocker):
    from pykour.internal.handler.request import call

    async def func():
        return "1"

    request = MagicMock()
    response = MagicMock()

    mocker.patch("pykour.internal.handler.request.bind_args", return_value=({}, None))
    result = await call(func, request, response)

    assert result == "1"


@pytest.mark.asyncio
async def test_call_with_connection(mocker):
    from pykour.internal.handler.request import call
    from pykour.db.connection import Connection

    def func(c: Connection):
        return "1"

    pool = MagicMock()
    conn = MagicMock()
    app = MagicMock()
    app.pool = pool
    request = MagicMock()
    request.app = app
    response = MagicMock()

    mocker.patch("pykour.internal.handler.request.bind_args", return_value=({"c": conn}, conn))
    result = await call(func, request, response)

    assert result == "1"
    conn.commit.assert_called_once()
    conn.rollback.assert_not_called()
    pool.release_connection.assert_called_once()


@pytest.mark.asyncio
async def test_call_throw_exception(mocker):
    from pykour.internal.handler.request import call
    from pykour.db.connection import Connection

    def func(c: Connection):
        raise ValueError("Error")

    pool = MagicMock()
    conn = MagicMock()
    app = MagicMock()
    app.pool = pool
    request = MagicMock()
    request.app = app
    response = MagicMock()

    mocker.patch("pykour.internal.handler.request.bind_args", return_value=({"c": conn}, conn))
    with pytest.raises(ValueError):
        await call(func, request, response)

    conn.commit.assert_not_called()
    conn.rollback.assert_called_once()
    pool.release_connection.assert_called_once()


def test_append_path_params():
    from pykour.internal.handler.request import append_path_params
    from pykour.request import Request

    route = MagicMock()
    route.path_params = {"id": "1"}

    app = MagicMock()
    app.get_route.return_value = route

    request = MagicMock(spec=Request)
    request.app = app
    request.path = "/users/1"
    request.method = "GET"
    request.path_params = {}

    append_path_params(request)

    assert request.path_params == {"id": "1"}
