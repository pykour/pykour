import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Any
from unittest import mock
from unittest.mock import Mock, AsyncMock, MagicMock

import pytest

from pykour import Response, Request, Pykour, Config
from pykour.call import call
from pykour.db import Connection
from pykour.schema import BaseSchema


@pytest.mark.asyncio
async def test_function_call_with_valid_int_parameter():
    async def func(x: int):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "123"}
    request.pool = None
    response = MagicMock(spec=Response)

    result = await call(func, request, response)
    assert result == 123


@pytest.mark.asyncio
async def test_function_call_with_valid_float_parameter():
    async def func(x: float):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "123.45"}
    request.pool = None
    response = MagicMock(spec=Response)

    result = await call(func, request, response)
    assert result == 123.45


@pytest.mark.asyncio
async def test_function_call_with_valid_bool_parameter():
    async def func(x: bool):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "true"}
    request.pool = None
    response = MagicMock(spec=Response)

    result = await call(func, request, response)
    assert result is True


@pytest.mark.asyncio
async def test_function_call_with_valid_datetime_parameter():
    async def func(x: datetime):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "2023-10-01"}
    request.pool = None
    response = MagicMock(spec=Response)

    result = await call(func, request, response)
    assert result == datetime(2023, 10, 1)


@pytest.mark.asyncio
async def test_function_call_with_invalid_int_parameter():
    async def func(x: int):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "invalid"}
    request.pool = None
    response = MagicMock(spec=Response)

    with pytest.raises(ValueError):
        await call(func, request, response)


@pytest.mark.asyncio
async def test_function_call_with_invalid_float_parameter():
    async def func(x: float):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "invalid"}
    request.pool = None
    response = MagicMock(spec=Response)

    with pytest.raises(ValueError):
        await call(func, request, response)


@pytest.mark.asyncio
async def test_function_call_with_invalid_datetime_parameter():
    async def func(x: datetime):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "invalid-date"}
    request.pool = None
    response = MagicMock(spec=Response)

    with pytest.raises(ValueError):
        await call(func, request, response)


@pytest.mark.asyncio
async def test_function_call_with_missing_path_param():
    async def func(x: int):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {}
    request.pool = None
    response = MagicMock(spec=Response)

    logger = logging.getLogger("pykour")

    with mock.patch.object(logger, "isEnabledFor", return_value=True):
        with pytest.raises(TypeError):
            await call(func, request, response)


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


@pytest.mark.asyncio
async def test_function_call_with_valid_enum_parameter():
    async def func(x: Color):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "RED"}
    request.pool = None
    response = MagicMock(spec=Response)

    result = await call(func, request, response)
    assert result == Color.RED


@pytest.mark.asyncio
async def test_function_call_with_valid_str_parameter():
    async def func(x: str):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "hello"}
    request.pool = None
    response = MagicMock(spec=Response)

    result = await call(func, request, response)
    assert result == "hello"


@pytest.mark.asyncio
async def test_function_call_with_invalid_enum_parameter():
    async def func(x: Color):
        return x

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "INVALID_COLOR"}
    request.pool = None
    response = MagicMock(spec=Response)

    with pytest.raises(ValueError):
        await call(func, request, response)


@pytest.mark.asyncio
async def test_function_call_with_config(mocker):
    async def func(x: Color, config: Config):
        return x

    _config = Config("config.yaml")
    mocker.patch.object(Pykour, "config", _config)

    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {"x": "RED"}
    response = MagicMock(spec=Response)

    await call(func, request, response)


class TestSchema(BaseSchema):
    field: str


# サンプル関数
async def sample_function(schema: TestSchema, request: Request, response: Response):
    return {"schema": schema.field, "request": request.scope, "response": response.status}


def sample_sync_function(schema: TestSchema, request: Request, response: Response):
    return {"schema": schema.field, "request": request.scope, "response": response.status}


@pytest.fixture
def scope() -> Dict[str, Any]:
    return {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json; charset=utf-8")],
        "path_params": {},
        "app": Pykour(),
    }


@pytest.fixture
def dummy_request(scope) -> Request:
    receive = AsyncMock()
    receive.return_value = {"type": "http.request", "body": b'{"field": "value"}', "more_body": False}
    return Request(scope, receive)


@pytest.fixture
def dummy_response() -> Response:
    send = AsyncMock()
    return Response(send, 200)


# テストケース
@pytest.mark.asyncio
async def test_call_with_schema_request_response(dummy_request, dummy_response):
    result = await call(sample_function, dummy_request, dummy_response)
    assert result == {"schema": "value", "request": dummy_request.scope, "response": dummy_response.status}


@pytest.mark.asyncio
async def test_call_with_sync_function(dummy_request, dummy_response):
    result = await call(sample_sync_function, dummy_request, dummy_response)
    assert result == {"schema": "value", "request": dummy_request.scope, "response": dummy_response.status}


async def dummy_function(data: dict):
    return data


@pytest.mark.asyncio
async def test_call_with_dict_annotation():
    # Mock the request and response objects
    request = MagicMock(spec=Request)
    request.scope = {"app": Pykour()}
    request.path_params = {}
    request.pool = None
    response = MagicMock(spec=Response)

    request.json = AsyncMock(return_value={"key": "value"})

    func = dummy_function

    result = await call(func, request, response)

    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_call_with_connection():
    async def func(conn: Connection):
        return conn

    app = Pykour()
    app.pool = MagicMock()
    request = MagicMock(spec=Request)
    request.scope = {"app": app}
    request.path_params = {}
    response = MagicMock(spec=Response)

    result = await call(func, request, response)
    request.scope["app"].pool.get_connection.assert_called_once()


@pytest.mark.asyncio
async def test_call_with_connection_raise_error(mocker):
    async def func(conn: Connection):
        raise ValueError("Error")

    app = Pykour()
    app.pool = MagicMock()
    mocker.patch.object(app.pool, "get_connection", return_value=MagicMock(spec=Connection))
    request = MagicMock(spec=Request)
    request.scope = {"app": app}
    request.path_params = {}
    response = MagicMock(spec=Response)

    with pytest.raises(ValueError):
        await call(func, request, response)


@pytest.mark.asyncio
async def test_call_with_connection_twice():
    async def func(conn: Connection, conn2: Connection):
        return conn

    app = Pykour()
    app.pool = MagicMock()
    request = MagicMock(spec=Request)
    request.scope = {"app": app}
    request.path_params = {}
    response = MagicMock(spec=Response)

    result = await call(func, request, response)
    request.scope["app"].pool.get_connection.assert_called_once()


@pytest.mark.asyncio
async def test_call_with_connection_no_pool():
    async def func(conn: Connection):
        return conn

    app = Pykour()
    app.pool = None
    request = MagicMock(spec=Request)
    request.scope = {"app": app}
    request.path_params = {}
    response = MagicMock(spec=Response)

    result = await call(func, request, response)
    assert result is None
