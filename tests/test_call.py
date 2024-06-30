import json
from datetime import datetime
from enum import Enum
from unittest.mock import Mock

import pytest

from pykour.call import call
from pykour.request import Request
from pykour.response import Response


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


@pytest.mark.asyncio
async def test_function_call_with_int_parameter():
    async def func(x: int):
        return x

    result = await call(func, {"x": "1"}, Mock(spec=Request), Mock(spec=Response))
    assert result == 1


@pytest.mark.asyncio
async def test_function_call_with_float_parameter():
    async def func(x: float):
        return x

    result = await call(func, {"x": "1.1"}, Mock(spec=Request), Mock(spec=Response))
    assert result == 1.1


@pytest.mark.asyncio
async def test_function_call_with_bool_parameter():
    async def func(x: bool):
        return x

    result = await call(func, {"x": "true"}, Mock(spec=Request), Mock(spec=Response))
    assert result is True


@pytest.mark.asyncio
async def test_function_call_with_datetime_parameter():
    async def func(x: datetime):
        return x

    result = await call(func, {"x": "2022-01-01"}, Mock(spec=Request), Mock(spec=Response))
    assert result == datetime(2022, 1, 1)


@pytest.mark.asyncio
async def test_function_call_with_request_response_parameters():
    async def func(request: Request, response: Response):
        return request, response

    request = Mock(spec=Request)
    response = Mock(spec=Response)
    result_request, result_response = await call(func, {}, request, response)
    assert result_request is request
    assert result_response is response


@pytest.mark.asyncio
async def test_function_call_with_missing_variable():
    async def func(x: int):
        return x

    with pytest.raises(TypeError):
        await call(func, {}, Mock(spec=Request), Mock(spec=Response))


@pytest.mark.asyncio
async def test_function_call_with_enum_parameter():
    async def func(x: Color):
        return x

    result = await call(func, {"x": "RED"}, Mock(spec=Request), Mock(spec=Response))
    assert result == Color.RED


@pytest.mark.asyncio
async def test_function_call_with_invalid_enum_parameter():
    async def func(x: Color):
        return x

    with pytest.raises(ValueError):
        await call(func, {"x": "PURPLE"}, Mock(spec=Request), Mock(spec=Response))


@pytest.mark.asyncio
async def test_function_call_with_dict_parameter():
    async def func(x: dict):
        return x

    result = await call(
        func,
        {"x": json.dumps({"key": "value"})},
        Mock(spec=Request),
        Mock(spec=Response),
    )
    assert result == {"key": "value"}


@pytest.mark.asyncio
async def test_function_call_with_str_parameter():
    async def func(x: str):
        return x

    result = await call(func, {"x": "hello"}, Mock(spec=Request), Mock(spec=Response))
    assert result == "hello"


@pytest.mark.asyncio
async def test_function_call_with_invalid_dict_parameter():
    async def func(x: dict):
        return x

    with pytest.raises(json.JSONDecodeError):
        await call(func, {"x": "not a valid json"}, Mock(spec=Request), Mock(spec=Response))
