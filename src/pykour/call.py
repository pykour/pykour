import inspect
import logging
from datetime import datetime
from typing import Any, Callable, Dict, get_origin
from enum import Enum

from pykour.config import Config
from pykour.db.connection import Connection
from pykour.request import Request
from pykour.response import Response
from pykour.schema import BaseSchema


def cast_to_type(value: Any, to_type: type) -> Any:
    if to_type == int:
        return int(value)
    elif to_type == float:
        return float(value)
    elif to_type == bool:
        return value.lower() in ["true", "1", "yes"]
    elif to_type == datetime:
        return datetime.strptime(value, "%Y-%m-%d")
    elif issubclass(to_type, Enum):
        try:
            return to_type[value]
        except KeyError:
            raise ValueError(f"{value} is not a valid {to_type.__name__}")
    else:
        return value


async def call(func: Callable, request: Request, response: Response) -> Any:
    sig = inspect.signature(func)
    logger = logging.getLogger("pykour")

    path_params = request.path_params
    app = request.scope.get("app")
    pool = app.pool
    conn = None

    bound_args: Dict[str, Any] = {}

    for param_name, param in sig.parameters.items():
        if isinstance(param.annotation, type) and issubclass(param.annotation, BaseSchema):
            bound_args[param_name] = param.annotation.from_dict(await request.json())
        elif param.annotation is dict or get_origin(param.annotation) is dict:
            bound_args[param_name] = await request.json()
        elif param.annotation is Request or param_name == "request" or param_name == "req":
            bound_args[param_name] = request
        elif param.annotation is Response or param_name == "response" or param_name == "res" or param_name == "resp":
            bound_args[param_name] = response
        elif param_name in path_params:
            bound_args[param_name] = cast_to_type(path_params[param_name], param.annotation)
        elif request.scope.get("app").config and (param.annotation is Config or param_name == "config"):
            bound_args[param_name] = request.get("app").config
        elif param.annotation is Connection or param_name == "conn" or param_name == "connection":
            if pool:
                if conn:
                    bound_args[param_name] = conn
                else:
                    conn = pool.get_connection()
                    bound_args[param_name] = conn
            else:
                bound_args[param_name] = None

    try:
        result = func(**bound_args)
        ret = None
        if inspect.iscoroutine(result):
            ret = await result
        else:
            ret = result

        if conn:
            conn.commit()
        return ret
    except Exception as e:
        if logger.isEnabledFor(logging.ERROR):
            logger.error(f"Error occurred while calling {func.__name__}: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            pool.release_connection(conn)
