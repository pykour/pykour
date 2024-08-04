import logging
import time
from http import HTTPStatus

import pykour.handler.request as request_handler
import pykour.handler.response as response_handler
import pykour.exceptions as ex
from pykour.logging import write_access_log

from pykour.request import Request
from pykour.response import Response
from pykour.types import Scope, Receive, Send


class ASGIApp:
    """ASGI application class."""

    def __init__(self):
        """Initialize Pykour application."""
        self._logger = logging.getLogger("pykour")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive)
        response = Response(send)
        start_time = time.perf_counter()
        try:
            # Check if the scheme is supported
            if not request_handler.is_supported_scheme(request):
                await response_handler.handle_error(request, response, HTTPStatus.BAD_REQUEST)
                return

            # Check if the method is supported
            if not request_handler.is_supported_method(request):
                if self._logger.isEnabledFor(logging.DEBUG):
                    self._logger.debug(f"Unsupported HTTP Method: {request.method}")
                await response_handler.handle_error(request, response, HTTPStatus.NOT_FOUND)
                return

            # Check if the method is allowed
            if not request_handler.is_method_allowed(request):
                if self._logger.isEnabledFor(logging.DEBUG):
                    self._logger.debug(f"Method not allowed: {request.method}")
                await response_handler.handle_error(request, response, HTTPStatus.METHOD_NOT_ALLOWED)
                return

            # Process the request if the route valid
            if request_handler.is_valid_route(request):
                self.append_path_params(request)
                await self.handle_request(request, response)
            else:
                if self._logger.isEnabledFor(logging.DEBUG):
                    self._logger.debug(f"No valid route found: {request.method} {request.path}")
                await response_handler.handle_error(request, response, HTTPStatus.NOT_FOUND)

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

    async def handle_request(self, request: Request, response: Response):
        """Handle request for a route."""

        app = request.app
        route = app.get_route(request.path, request.method)
        route_fun, status_code = route.handler
        response.status = status_code

        # noinspection PyBroadException
        try:
            response_body = await request_handler.call(route_fun, request, response)

            await response_handler.handle_response(request, response, response_body)
        except ex.HTTPException as e:
            await response_handler.handle_http_exception(request, response, e)
        except Exception as e:
            if self._logger.isEnabledFor(logging.DEBUG):
                self._logger.debug(f"Internal Server Error: {e}")
            await response_handler.handle_error(request, response, HTTPStatus.INTERNAL_SERVER_ERROR)