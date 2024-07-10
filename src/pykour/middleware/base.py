from pykour.types import ASGIApp, Scope, Receive, Send


class BaseMiddleware:
    """Base middleware class."""

    def __init__(self, app: ASGIApp):
        """
        Initialize the middleware with the application.

        Args:
            app: The ASGI application.
        """
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ):
        """
        Call the middleware.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive channel.
            send: The ASGI send channel.
        """

        await self.process_request(scope, receive, send)
        await self.app(scope, receive, send)
        await self.process_response(scope, receive, send)

    async def process_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ):
        """
        Executed before the request is processed.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive channel.
            send: The ASGI send channel.
        """
        ...

    async def process_response(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ):
        """
        Executed after response processing.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive channel.
            send: The ASGI send channel.
        """
        ...
