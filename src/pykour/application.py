import json
from http import HTTPStatus
from typing import Callable

import pykour.exceptions as ex
from pykour.call import call
from pykour.config import Config
from pykour.request import Request
from pykour.response import Response
from pykour.router import Router


class Pykour:
    supported_protocols = ["http"]

    def __init__(self):
        self.router = Router()
        self._config = None

    def get(self, path: str, status_code=HTTPStatus.OK) -> Callable:
        return self.route("GET", path, status_code)

    def post(self, path: str, status_code=HTTPStatus.CREATED) -> Callable:
        return self.route("POST", path, status_code)

    def put(self, path: str, status_code=HTTPStatus.OK) -> Callable:
        return self.route("PUT", path, status_code)

    def delete(self, path: str, status_code=HTTPStatus.NO_CONTENT) -> Callable:
        return self.route("DELETE", path, status_code)

    def patch(self, path: str, status_code=HTTPStatus.OK) -> Callable:
        return self.route("PATCH", path, status_code)

    def options(self, path: str, status_code=HTTPStatus.OK) -> Callable:
        return self.route("OPTIONS", path, status_code)

    def head(self, path: str, status_code=HTTPStatus.OK) -> Callable:
        return self.route("HEAD", path, status_code)

    def trace(self, path: str, status_code=HTTPStatus.OK) -> Callable:
        return self.route("TRACE", path, status_code)

    def route(self, method: str, path: str, status_code: int) -> Callable:
        def decorator(func):
            self.router.add_route(path, method, (func, status_code))
            return func

        return decorator

    def use(self, middleware) -> None:
        if type(middleware) is Config:
            self._config = middleware
        elif type(middleware) is Router:
            self.router.add_router(middleware)

    async def __call__(self, scope, receive, send) -> None:
        self._is_supported_protocol(scope)

        response = await self._call(scope, receive, send)

        await response.render()

    async def _call(self, scope, receive, send) -> Response:
        path = scope["path"]
        method = scope["method"]

        if self.router.exists(path, method):
            route = self.router.get_route(path, method)
            route_fun, status_code = route.handler
            variables = route.variables
            if route_fun:
                request = Request(scope, receive)
                response = Response(send, status_code)
                try:
                    response_body = await call(route_fun, variables, request, response)
                    if type(response_body) is dict or type(response_body) is list:
                        response.content = json.dumps(response_body)
                        response.content_type = "application/json"
                    elif type(response_body) is str:
                        response.content = response_body
                        response.content_type = "text/plain"
                    else:
                        raise ValueError("Unsupported response type: %s" % type(response_body))
                except ex.HTTPException as e:
                    response = Response(
                        send,
                        status_code=e.status_code,
                        content_type="text/plain",
                    )
                    response.content = e.message
                except Exception as e:
                    response = Response(send, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)
                    response.content = str(e)

            else:
                response = Response(send, status_code=HTTPStatus.NOT_FOUND, content_type="text/plain")
        else:
            response = Response(send, status_code=HTTPStatus.NOT_FOUND, content_type="text/plain")
            response.content = "Not Found"
            response.content = "Not Found"

        return response

    def _is_supported_protocol(self, scope) -> None:
        if scope["type"] not in self.supported_protocols:
            raise ValueError("Unsupported scope type: %s" % scope["type"])
