import logging
from uuid import uuid4

from pykour.middleware import BaseMiddleware
from pykour.types import Scope, Receive, Send, Message, ASGIApp

from pykour.globals import thread_local


class UUIDMiddleware(BaseMiddleware):

    def __init__(self, app, header_name="X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name
        self.logger = logging.getLogger("uvicorn")

    async def process_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ):
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
        if self.logger.isEnabledFor(logging.INFO):
            self.logger.info(f"{self.header_name}: {scope['request_id']}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
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


def uuid_middleware(header_name="x-request-id"):
    def middleware(app: ASGIApp):
        return UUIDMiddleware(app, header_name=header_name)

    return middleware
