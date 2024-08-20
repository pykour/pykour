from typing import Callable
from uuid import uuid4

from pykour.logging import write_info_log
from pykour.middleware import BaseMiddleware
from pykour.types import Scope, Receive, Send, Message, ASGIApp

from pykour.globals import thread_local


class UUIDMiddleware(BaseMiddleware):
    """
    The UUIDMiddleware generates a unique ID for each request and adds it to the request and response header.
    The unique ID is generated using UUIDv4 and is added to the header `X-Request-ID` by default.

    If you wish to specify an arbitrary header name, use the `header_name` argument.

    ```
    from pykour import Pykour
    from pykour.middleware import uuid_middleware

    app = Pykour()
    app.add_middleware(uuid_middleware("X-CUSTOM-REQUEST-ID"))
    ```

    In this example, a unique ID is added to the header ``X-CUSTOM-REQUEST-ID``.

    If you are using middleware such as distributed tracing to generate a unique request ID before invoking
    the application,
    you can use that ID to set the request ID.

    ````
    from pykour import Pykour
    from pykour.middleware import uuid_middleware

    app = Pykour()
    app.add_middleware(uuid_middleware("X-TRACE-ID"))
    ```

    This example takes a request with a header `X-TRACE-ID` and uses that ID as the request ID.
    In this case, the UUIDMiddleware uses the value of the `X-TRACE-ID` header as the request ID if it exists and
    does not generate a new request ID.

    The request ID is only added to the request header and does not affect the processing of the request.
    It is also added to the response header.
    The use of UUIDMiddleware facilitates tracing and debugging of requests.
    """

    def __init__(self, app, header_name="X-Request-ID"):
        """
        Initialize the middleware with the application.

        Args:
            app: The ASGI application.
            header_name: The name of the header to add the request ID to. Default is `X-Request-ID`.
        """
        super().__init__(app)
        self.header_name = header_name

    async def process_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ):
        """
        Process the request and generate a unique request ID.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive channel.
            send: The ASGI send channel.
        """

        # generate default request_id
        request_id = str(uuid4())

        # check if X-Request-ID exists in headers
        for header in scope["headers"]:
            if header[0].decode("latin1") == self.header_name:
                request_id = header[1].decode("latin1")
                break

        # if not, add X-Request-ID to headers
        if not any(header[0].decode("latin1") == self.header_name for header in scope["headers"]):
            scope["headers"].append((self.header_name.encode("latin1"), request_id.encode("latin1")))

        scope["request_id"] = request_id
        thread_local.request_id = request_id
        write_info_log(f"{self.header_name}: {scope['request_id']}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        """
        Call the middleware.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive channel.
            send: The ASGI send channel.
        """

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        self.scope = scope
        self.send = send
        await self.process_request(scope, receive, send)
        await self.app(scope, receive, self.send_with_request_id)

    async def send_with_request_id(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            message["headers"].append((self.header_name.encode("latin1"), self.scope["request_id"].encode()))
        await self.send(message)


def uuid_middleware(header_name="x-request-id") -> Callable[[ASGIApp], ASGIApp]:
    """
    Middleware that adds a unique request ID to the request and response headers.

    Args:
        header_name: The name of the header to add the request ID to. Default is `X-Request-ID`.
    Returns:
        A middleware function that adds a unique request ID to the request and response
    """

    def middleware(app: ASGIApp):
        return UUIDMiddleware(app, header_name=header_name)

    return middleware
