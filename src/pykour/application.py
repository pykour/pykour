import logging
import time
import json
import os
from http import HTTPStatus
from typing import Callable, Any

import pykour.exceptions as ex
from pykour.config import Config
from pykour.call import call
from pykour.db.pool import ConnectionPool
from pykour.logging import setup_logging, write_access_log


from pykour.request import Request
from pykour.response import Response
from pykour.router import Router
from pykour.types import Scope, Receive, Send, ASGIApp
from colorama import Fore


STATUS_COLORS = {
    "2xx": Fore.GREEN,
    "3xx": Fore.BLUE,
    "4xx": Fore.YELLOW,
    "5xx": Fore.RED,
}


class Pykour(Router):
    SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]

    def __init__(self, prefix="/", config: str = None):
        super().__init__(prefix=prefix)

        self._config = Config(config) if config else Config()
        setup_logging(self._config.get_log_levels())
        self.production_mode = os.getenv("PYKOUR_ENV") == "production"
        self.app: ASGIApp = RootASGIApp()
        self.logger = logging.getLogger("pykour")
        if self._config.get_datasource_type():
            self.pool = ConnectionPool(self._config)
        else:
            self.pool = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        await self.app(scope, receive, send)

    @property
    def config(self) -> Config:
        return self._config

    def add_middleware(self, middleware: Callable, **kwargs: Any) -> None:
        """Add middleware to the application.

        Args:
            middleware: Middleware class.
            kwargs: Middleware arguments.
        """

        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"Add middleware: {middleware.__name__}")
        self.app = middleware(self.app, **kwargs)


class RootASGIApp:
    """Pykour application class."""

    SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]

    def __init__(self):
        """Initialize Pykour application."""
        self.logger = logging.getLogger("pykour")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive)
        response = Response(send)
        start_time = time.perf_counter()
        try:
            # Check if the scheme is supported
            if not self.is_supported_scheme(request):
                await self.handle_bad_request(request, response)
                return

            # Check if the method is supported
            if not self.is_supported_method(request):
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Unsupported HTTP Method: {request.method}")
                await self.handle_not_found(request, response)
                return

            # Check if the method is allowed
            if not self.is_method_allowed(request):
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Method not allowed: {request.method}")
                await self.handle_method_not_allowed(request, response)
                return

            # Process the request if the route exists
            if self.exists_route(request):
                self.append_path_params(request)
                await self.handle_request(self, request, response)
            else:
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Route not found: {request.path}")
                await self.handle_not_found(request, response)

        finally:
            end_time = time.perf_counter()
            write_access_log(request, response, (end_time - start_time) * 1000)

    @staticmethod
    def append_path_params(request: Request) -> None:
        """Append path parameters to the request."""
        app = request.app
        path = request.path
        method = request.method
        route = app.get_route(path, method)

        path_params = route.path_params
        request.path_params = path_params

    @staticmethod
    async def handle_bad_request(request: Request, response: Response) -> None:
        response.status = HTTPStatus.BAD_REQUEST
        response.content_type = "text/plain"
        response.content = HTTPStatus.BAD_REQUEST.phrase
        for accept in request.accept:
            if accept in ["application/json"]:
                response.content_type = accept
                response.content = json.dumps({"error": HTTPStatus.BAD_REQUEST.phrase})
                break
        await response.render()

    @staticmethod
    async def handle_not_found(request: Request, response: Response) -> None:
        response.status = HTTPStatus.NOT_FOUND
        response.content_type = "text/plain"
        response.content = HTTPStatus.NOT_FOUND.phrase
        for accept in request.accept:
            if accept in ["application/json"]:
                response.content_type = accept
                response.content = json.dumps({"error": HTTPStatus.NOT_FOUND.phrase})
                break
        await response.render()

    @staticmethod
    async def handle_method_not_allowed(request: Request, response: Response) -> None:
        response.status = HTTPStatus.METHOD_NOT_ALLOWED
        response.content_type = "text/plain"
        response.content = HTTPStatus.METHOD_NOT_ALLOWED.phrase
        for accept in request.accept:
            if accept in ["application/json"]:
                response.content_type = accept
                response.content = json.dumps({"error": HTTPStatus.METHOD_NOT_ALLOWED.phrase})
                break
        await response.render()

    @staticmethod
    async def handle_internal_server_error(request: Request, response: Response) -> None:
        response.status = HTTPStatus.INTERNAL_SERVER_ERROR
        response.content_type = "text/plain"
        response.content = HTTPStatus.INTERNAL_SERVER_ERROR.phrase
        for accept in request.accept:
            if accept in ["application/json"]:
                response.content_type = accept
                response.content = json.dumps({"error": HTTPStatus.INTERNAL_SERVER_ERROR.phrase})
                break
        await response.render()

    @staticmethod
    async def handle_http_exception(request: Request, response: Response, e: ex.HTTPException) -> None:
        response.status = e.status_code
        response.content_type = "text/plain"
        response.content = e.message
        for accept in request.accept:
            if accept in ["application/json"]:
                response.content_type = accept
                response.content = json.dumps({"error": e.message})
                break
        await response.render()

    @staticmethod
    async def handle_request(self, request: Request, response: Response):
        """Handle request for a route."""

        app = request.app
        route = app.get_route(request.path, request.method)
        route_fun, status_code = route.handler
        response.status = status_code

        # noinspection PyBroadException
        try:
            response_body = await call(route_fun, request, response)

            if response.status == HTTPStatus.NO_CONTENT:
                response.content = ""
                response.content_type = "text/plain"
            elif request.method == "OPTIONS":
                response.add_header("Allow", ", ".join(app.get_allowed_methods(request.path)))
                response.content = ""
            elif request.method == "HEAD":
                response.add_header("Content-Length", str(len(str(response_body))))
                response.content = ""
            elif isinstance(response_body, (dict, list)):
                response.content = json.dumps(response_body)
                response.content_type = "application/json"
            elif isinstance(response_body, str):
                response.content = response_body
                response.content_type = "text/plain"
            else:
                raise ValueError("Unsupported response type: %s" % type(response_body))

            await response.render()
        except ex.HTTPException as e:
            await self.handle_http_exception(request, response, e)
        except Exception as e:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"Internal Server Error: {e}")
            await self.handle_internal_server_error(request, response)

    @staticmethod
    def is_supported_scheme(request: Request) -> bool:
        """Check if the scheme is supported."""
        return request.scheme in ["HTTP"]

    @staticmethod
    def is_supported_method(request: Request) -> bool:
        """Check if the method is supported."""
        return request.method in RootASGIApp.SUPPORTED_METHODS

    @staticmethod
    def is_method_allowed(request: Request) -> bool:
        """Check if the method is allowed for the given path."""
        app = request.app
        path = request.path
        method = request.method
        allowed_methods = app.get_allowed_methods(path)
        return allowed_methods == [] or method in allowed_methods

    @staticmethod
    def exists_route(request: Request) -> bool:
        """Check if the route exists."""
        app = request.app
        path = request.path
        method = request.method
        return app.exists(path, method)
