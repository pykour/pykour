import logging
from uuid import uuid4

from pykour.middleware import BaseMiddleware
from pykour.types import Scope, Receive, Send, Message


class RequestIDMiddleware(BaseMiddleware):

    def __init__(self, app):
        super().__init__(app)
        self.logger = logging.getLogger("uvicorn")

    async def process_request(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ):
        # デフォルトのUUIDを生成
        request_id = str(uuid4())

        # scopeからX-Request-IDヘッダーをチェック
        for header in scope["headers"]:
            if header[0].decode("latin1") == "x-request-id":
                request_id = header[1].decode("latin1")
                break

        # 新しいX-Request-IDをヘッダーに追加（存在しない場合）
        if not any(header[0].decode("latin1") == "x-request-id" for header in scope["headers"]):
            scope["headers"].append((b"x-request-id", request_id.encode("latin1")))

        scope["request_id"] = request_id
        self.logger.info(f"REQUEST ID: {scope['request_id']}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        self.scope = scope
        self.send = send
        await self.process_request(scope, receive, send)
        await self.app(scope, receive, self.send_with_request_id)

    async def send_with_request_id(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            message["headers"].append((b"X-Request-ID", self.scope["request_id"].encode()))
        await self.send(message)
