import json
from datetime import datetime
from enum import Enum
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

import pytest

from pykour import Response, Request, Pykour
from pykour.call import call
from pykour.schema import BaseSchema


@pytest.mark.asyncio
async def test_function_call_with_valid_int_parameter():
    async def func(x: int):
        return x

    result = await call(func, Mock(spec=Request, scope={"path_params": {"x": "123"}}), Mock(spec=Response))
    assert result == 123


@pytest.mark.asyncio
async def test_function_call_with_valid_float_parameter():
    async def func(x: float):
        return x

    result = await call(func, Mock(spec=Request, scope={"path_params": {"x": "123.45"}}), Mock(spec=Response))
    assert result == 123.45


@pytest.mark.asyncio
async def test_function_call_with_valid_bool_parameter():
    async def func(x: bool):
        return x

    result = await call(func, Mock(spec=Request, scope={"path_params": {"x": "true"}}), Mock(spec=Response))
    assert result is True


@pytest.mark.asyncio
async def test_function_call_with_valid_datetime_parameter():
    async def func(x: datetime):
        return x

    result = await call(func, Mock(spec=Request, scope={"path_params": {"x": "2023-10-01"}}), Mock(spec=Response))
    assert result == datetime(2023, 10, 1)


@pytest.mark.asyncio
async def test_function_call_with_valid_dict_parameter():
    async def func(x: dict):
        return x

    result = await call(func, Mock(spec=Request, scope={"path_params": {"x": '{"key": "value"}'}}), Mock(spec=Response))
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_function_call_with_invalid_int_parameter():
    async def func(x: int):
        return x

    with pytest.raises(ValueError):
        await call(func, Mock(spec=Request, scope={"path_params": {"x": "invalid"}}), Mock(spec=Response))


@pytest.mark.asyncio
async def test_function_call_with_invalid_float_parameter():
    async def func(x: float):
        return x

    with pytest.raises(ValueError):
        await call(func, Mock(spec=Request, scope={"path_params": {"x": "invalid"}}), Mock(spec=Response))


@pytest.mark.asyncio
async def test_function_call_with_invalid_datetime_parameter():
    async def func(x: datetime):
        return x

    with pytest.raises(ValueError):
        await call(func, Mock(spec=Request, scope={"path_params": {"x": "invalid-date"}}), Mock(spec=Response))


@pytest.mark.asyncio
async def test_function_call_with_invalid_dict_parameter():
    async def func(x: dict):
        return x

    with pytest.raises(json.JSONDecodeError):
        await call(func, Mock(spec=Request, scope={"path_params": {"x": "invalid-json"}}), Mock(spec=Response))


@pytest.mark.asyncio
async def test_function_call_with_missing_path_param():
    async def func(x: int):
        return x

    with pytest.raises(TypeError):
        await call(func, Mock(spec=Request, scope={"path_params": {}, "app": Pykour()}), Mock(spec=Response))


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


@pytest.mark.asyncio
async def test_function_call_with_valid_enum_parameter():
    async def func(x: Color):
        return x

    result = await call(func, Mock(spec=Request, scope={"path_params": {"x": "RED"}}), Mock(spec=Response))
    assert result == Color.RED


@pytest.mark.asyncio
async def test_function_call_with_valid_str_parameter():
    async def func(x: str):
        return x

    result = await call(func, Mock(spec=Request, scope={"path_params": {"x": "hello"}}), Mock(spec=Response))
    assert result == "hello"


@pytest.mark.asyncio
async def test_function_call_with_invalid_enum_parameter():
    async def func(x: Color):
        return x

    with pytest.raises(ValueError):
        await call(func, Mock(spec=Request, scope={"path_params": {"x": "INVALID_COLOR"}}), Mock(spec=Response))


class TestSchema(BaseSchema):
    field: str


# サンプル関数
async def sample_function(schema: TestSchema, request: Request, response: Response):
    return {"schema": schema.field, "request": request.scope, "response": response.status}


def sample_sync_function(schema: TestSchema, request: Request, response: Response):
    return {"schema": schema.field, "request": request.scope, "response": response.status}


# モックリクエストを準備
@pytest.fixture
def scope() -> Dict[str, Any]:
    return {
        "type": "http",
        "method": "POST",
        "headers": [(b"content-type", b"application/json; charset=utf-8")],
        "path_params": {},
    }


@pytest.fixture
def dummy_request(scope) -> Request:
    send = AsyncMock()
    send.return_value = {"type": "http.request", "body": b'{"field": "value"}', "more_body": False}
    return Request(scope, send)


@pytest.fixture
def dummy_response() -> Response:
    receive = AsyncMock()
    return Response(receive, 200)


# テストケース
@pytest.mark.asyncio
async def test_call_with_schema_request_response(dummy_request: Request, dummy_response: Response):
    result = await call(sample_function, dummy_request, dummy_response)

    # 検証
    assert result == {"schema": "value", "request": dummy_request.scope, "response": dummy_response.status}


@pytest.mark.asyncio
async def test_call_with_sync_function(dummy_request: Request, dummy_response: Response):
    result = await call(sample_sync_function, dummy_request, dummy_response)
    assert result == {"schema": "value", "request": dummy_request.scope, "response": dummy_response.status}
