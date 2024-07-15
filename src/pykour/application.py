import json
import os
from http import HTTPStatus
from typing import Callable, Union, Dict, Any, MutableMapping

import pykour.exceptions as ex
from pykour.config import Config
from pykour.call import call
from pykour.middleware import BaseMiddleware
from pykour.request import Request
from pykour.response import Response
from pykour.router import Router
from pykour.types import Scope, Receive, Send, ASGIApp, HTTPStatusCode


class Pykour:
    SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]

    def __init__(self, config: str = None):
        self._config = Config(config) if config else None
        self.production_mode = os.getenv("PYKOUR_ENV") == "production"
        self.router = Router()
        self.app: ASGIApp = RootASGIApp()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        await self.app(scope, receive, send)

    @property
    def config(self) -> Config:
        return self._config

    def add_middleware(self, middleware: Callable, **kwargs: Dict[str, Any]) -> None:
        """Add middleware to the application.

        Args:
            middleware: Middleware class.
            kwargs: Middleware arguments.
        """
        self.app = middleware(self.app, **kwargs)

    def get(self, path: str, status_code: HTTPStatusCode = HTTPStatus.OK) -> Callable:
        """Decorator for GET method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="GET", status_code=status_code)

    def post(self, path: str, status_code: HTTPStatusCode = HTTPStatus.CREATED) -> Callable:
        """Decorator for POST method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="POST", status_code=status_code)

    def put(self, path: str, status_code: HTTPStatusCode = HTTPStatus.OK) -> Callable:
        """Decorator for PUT method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="PUT", status_code=status_code)

    def delete(self, path: str, status_code: HTTPStatusCode = HTTPStatus.NO_CONTENT) -> Callable:
        """Decorator for DELETE method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="DELETE", status_code=status_code)

    def patch(self, path: str, status_code: HTTPStatusCode = HTTPStatus.OK) -> Callable:
        """Decorator for PATCH method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="PATCH", status_code=status_code)

    def options(self, path: str, status_code: HTTPStatusCode = HTTPStatus.OK) -> Callable:
        """Decorator for OPTIONS method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="OPTIONS", status_code=status_code)

    def head(self, path: str, status_code: HTTPStatusCode = HTTPStatus.OK) -> Callable:
        """Decorator for HEAD method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="HEAD", status_code=status_code)

    def route(self, path: str, method: str = "GET", status_code: HTTPStatusCode = HTTPStatus.OK) -> Callable:
        """Decorator for route.

        Args:
            path: URL path.
            method: HTTP method.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """

        if method not in self.SUPPORTED_METHODS:
            raise ValueError(f"Unsupported HTTP method: {method}")

        def decorator(func):
            self.router.add_route(path=path, method=method, handler=(func, status_code))
            return func

        return decorator

    def add_router(self, router: Router) -> None:
        """Add a router to the application.

        Args:
            router: Router object.
        """
        self.router.add_router(router)


class RootASGIApp:
    """Pykour application class."""

    def __init__(self):
        """Initialize Pykour application."""
        ...

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await RootASGIApp.handle_error(send, HTTPStatus.BAD_REQUEST, "Bad Request")
            return

        app = scope["app"]
        path = scope["path"]
        method = scope["method"]

        # Check if the method is supported
        if method not in Pykour.SUPPORTED_METHODS:
            await RootASGIApp.handle_error(send, HTTPStatus.NOT_FOUND, "Not Found")
            return

        # Check if the method is allowed
        if not RootASGIApp.is_method_allowed(scope):
            await RootASGIApp.handle_error(send, HTTPStatus.METHOD_NOT_ALLOWED, "Method Not Allowed")
            return

        # Process the request if the route exists
        if app.router.exists(path, method):
            await self.handle_route(scope, receive, send)
        else:
            await self.handle_error(send, HTTPStatus.NOT_FOUND, "Not Found")

    @staticmethod
    def is_method_allowed(scope: Scope) -> bool:
        """Check if the method is allowed for the given path."""
        app = scope["app"]
        path = scope["path"]
        method = scope["method"]
        allowed_methods = app.router.get_allowed_methods(path)
        return allowed_methods == [] or method in allowed_methods

    @staticmethod
    async def handle_route(scope: Scope, receive: Receive, send: Send):
        """Handle request for an existing route."""
        app = scope["app"]
        path = scope["path"]
        method = scope["method"]

        route = app.router.get_route(path, method)
        route_fun, status_code = route.handler
        path_params = route.path_params
        scope["path_params"] = path_params
        request = Request(scope, receive)
        response = Response(send, status_code)

        try:
            response_body = await RootASGIApp.process_request(route_fun, request, response)
            await RootASGIApp.prepare_response(scope, request, response, response_body)
        except ex.HTTPException as e:
            await RootASGIApp.handle_error(send, e.status_code, e.message)
        except Exception as e:
            await RootASGIApp.handle_error(send, HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    @staticmethod
    async def process_request(route_fun: Callable, request: Request, response: Response):
        """Process the request and return the response body."""
        return await call(route_fun, request, response)

    @staticmethod
    async def prepare_response(scope: Scope, request: Request, response: Response, response_body):
        """Prepare the response based on the request method and response body."""
        app = scope["app"]
        path = scope["path"]
        method = scope["method"]
        if isinstance(response_body, (dict, list)):
            response.content = json.dumps(response_body)
            response.content_type = "application/json"
        elif isinstance(response_body, str):
            response.content = response_body
            response.content_type = "text/plain"

        if response.status == HTTPStatus.NO_CONTENT:
            response.content = ""

        if method == "OPTIONS":
            response.add_header("Allow", ", ".join(app.router.get_allowed_methods(path)))
            response.content = ""
        elif method == "HEAD":
            response.add_header("Content-Length", str(len(str(response_body))))
            response.content = ""

        if response.content_type is None:
            raise ValueError("Unsupported response type: %s" % type(response_body))

        await response.render()

    @staticmethod
    async def handle_error(send: Send, status_code: Union[HTTPStatus, int], message: str):
        response = Response(send, status_code=status_code, content_type="text/plain")
        response.content = message
        await response.render()
