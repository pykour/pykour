import inspect
from typing import get_type_hints, Any

from pykour.schema import BaseSchema

TYPE_MAP = {
    int: "integer",
    str: "string",
    bool: "boolean",
    float: "number",
    list: "array",
    dict: "object",
}


def get_openapi_type(py_type: Any) -> str:
    """Pythonの型をOpenAPIの型に変換"""
    if hasattr(py_type, "__origin__"):
        origin = py_type.__origin__
        if origin is list:
            return "array"
        elif origin is dict:
            return "object"
        # 他のジェネリック型の処理
    return TYPE_MAP.get(py_type, "object")


def generate_openapi(app, scheme: str, hostname, port):
    openapi = {
        "openapi": "3.0.0",
        "info": {
            "summary": app.summary,
            "title": app.title,
            "version": app.version,
            "description": app.description,
        },
        "servers": [
            {
                "url": f"{scheme}://{hostname}:{port}/",
            }
        ],
        "paths": generate_openapi_paths(app),
    }

    return openapi


def generate_openapi_paths(app):
    paths: dict = {}

    try:
        for path, endpoint in app.get_openapi_routes():
            if path not in paths:
                paths[path] = {}
            method, handlers = endpoint
            handler, port = handlers

            paths[path][method.lower()] = {
                "summary": handler.__doc__.strip(),
            }

            # if parameters exist, add them to the path
            # parameters = generate_openapi_parameters(handler)
            # if parameters:
            #     paths[path][method.lower()]["parameters"] = parameters

            # if request body exists, add it to the path
            request_body = generate_openapi_request_body(handler)
            if request_body:
                paths[path][method.lower()]["requestBody"] = request_body

            responses = generate_openapi_responses(port)
            if responses:
                paths[path][method.lower()]["responses"] = responses
    except Exception as e:
        print(e)

    return paths


def generate_openapi_responses(port):
    return {
        f"{port}": {
            "description": "Successful response",
        }
    }


def generate_openapi_request_body(handler):
    sig = inspect.signature(handler)

    for param_name, param in sig.parameters.items():
        if isinstance(param.annotation, type) and issubclass(param.annotation, BaseSchema):
            return {
                "content": {
                    "application/json": {
                        "schema": generate_openapi_request_body_parameters(param.annotation),
                    }
                }
            }


def generate_openapi_request_body_parameters(annotation):
    schema: dict = {
        "type": "object",
        "properties": {},
    }

    for field_name, field in get_type_hints(annotation).items():
        schema["properties"][field_name] = {
            "type": get_openapi_type(field),
        }

    return schema
