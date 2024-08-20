import inspect
from typing import Any, Dict, get_origin, Tuple, ItemsView, Callable

from pykour.config import Config
from pykour.db.connection import Connection
from pykour.logging import write_error_log
from pykour.request import Request
from pykour.response import Response
from pykour.schema import BaseSchema
from pykour.util import cast

SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]


def is_supported_scheme(request: Request) -> bool:
    """Check if the scheme is supported."""
    return request.scheme in ["HTTP"]


def is_supported_method(request: Request) -> bool:
    """Check if the method is supported."""
    return request.method in SUPPORTED_METHODS


def is_method_allowed(request: Request) -> bool:
    """Check if the method is allowed for the given path."""
    app = request.app
    path = request.path
    method = request.method
    allowed_methods = app.get_allowed_methods(path)
    return allowed_methods == [] or method in allowed_methods


def is_valid_route(request: Request) -> bool:
    """Check if the route exists."""
    app = request.app
    path = request.path
    method = request.method
    return app.exists(path, method)


async def bind_args(
    request: Request, response: Response, items: ItemsView[str, inspect.Parameter]
) -> Tuple[Dict[str, Any], Connection]:
    bound_args: Dict[str, Any] = {}
    app = request.app
    pool = app.pool
    conn = None
    for param_name, param in items:
        if isinstance(param.annotation, type) and issubclass(param.annotation, BaseSchema):
            # Bind schema
            bound_args[param_name] = param.annotation.from_dict(await request.json())
        elif param.annotation is dict or get_origin(param.annotation) is dict:
            # Bind dictionary
            bound_args[param_name] = await request.json()
        elif param.annotation is Request or param_name == "request" or param_name == "req":
            # Bind request
            bound_args[param_name] = request
        elif param.annotation is Response or param_name == "response" or param_name == "res" or param_name == "resp":
            # Bind response
            bound_args[param_name] = response
        elif param_name in request.path_params:
            # Bind path parameters
            bound_args[param_name] = cast(request.path_params[param_name], param.annotation)
        elif param_name in request.query_params:
            # Bind query parameters
            bound_args[param_name] = cast(request.query_params[param_name], param.annotation)
        elif app.config and (param.annotation is Config or param_name == "config"):
            # Bind config
            bound_args[param_name] = app.config
        elif param.annotation is Connection or param_name == "conn" or param_name == "connection":
            if pool:
                if conn:
                    bound_args[param_name] = conn
                else:
                    conn = pool.get_connection()
                    bound_args[param_name] = conn
            else:
                bound_args[param_name] = None
        else:
            bound_args[param_name] = None

    return bound_args, conn


async def call(func: Callable, request: Request, response: Response) -> Any:
    sig = inspect.signature(func)
    app = request.app
    pool = app.pool

    bound_args, conn = await bind_args(request, response, sig.parameters.items())

    try:
        result = func(**bound_args)
        if inspect.iscoroutine(result):
            ret = await result
        else:
            ret = result

        if conn:
            conn.commit()
        return ret
    except Exception as e:
        write_error_log(f"Error occurred while calling {func.__name__}: {e}")
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            pool.release_connection(conn)
