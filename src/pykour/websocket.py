"""WebSocket support for Pykour."""

from __future__ import annotations

from collections.abc import AsyncIterator
from enum import IntEnum
from typing import Any
from urllib.parse import parse_qs

from pykour import json as pykour_json
from pykour.types import Receive, Scope, Send


class WebSocketState(IntEnum):
    """WebSocket connection state."""

    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2


class WebSocketDisconnect(Exception):
    """Raised when a WebSocket disconnects."""

    def __init__(self, code: int = 1000, reason: str = "") -> None:
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket disconnected: code={code}, reason={reason}")


class WebSocket:
    """WebSocket connection handler.

    Provides methods to accept connections, send/receive messages,
    and close connections.

    Example:
        routes/ws/chat/route.py:
        ```python
        from pykour import WebSocket
        from pykour.websocket import WebSocketDisconnect

        async def websocket(ws: WebSocket) -> None:
            await ws.accept()
            try:
                while True:
                    message = await ws.receive_text()
                    await ws.send_text(f"Echo: {message}")
            except WebSocketDisconnect:
                pass
        ```
    """

    def __init__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        path_params: dict[str, str] | None = None,
    ) -> None:
        """Initialize WebSocket connection.

        Args:
            scope: ASGI WebSocket scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
            path_params: Path parameters extracted from URL.
        """
        self._scope = scope
        self._receive = receive
        self._send = send
        self._state = WebSocketState.CONNECTING
        self._path_params = path_params or {}

    @property
    def scope(self) -> Scope:
        """Get the ASGI scope."""
        return self._scope

    @property
    def path(self) -> str:
        """Get the WebSocket path."""
        return str(self._scope.get("path", "/"))

    @property
    def path_params(self) -> dict[str, str]:
        """Get path parameters."""
        return self._path_params

    @property
    def query_params(self) -> dict[str, str | list[str]]:
        """Get query parameters."""
        query_string = self._scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string, keep_blank_values=True)
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}

    @property
    def headers(self) -> dict[str, str]:
        """Get connection headers."""
        raw_headers: list[tuple[bytes, bytes]] = self._scope.get("headers", [])
        return {k.decode("latin-1"): v.decode("latin-1") for k, v in raw_headers}

    @property
    def state(self) -> WebSocketState:
        """Get current connection state."""
        return self._state

    @property
    def client(self) -> tuple[str, int] | None:
        """Get client address (host, port)."""
        return self._scope.get("client")

    async def accept(
        self,
        subprotocol: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Accept the WebSocket connection.

        Args:
            subprotocol: Optional subprotocol to accept.
            headers: Optional response headers.

        Raises:
            RuntimeError: If already connected or disconnected.
        """
        if self._state != WebSocketState.CONNECTING:
            raise RuntimeError(f"Cannot accept in state {self._state.name}")

        message: dict[str, Any] = {"type": "websocket.accept"}
        if subprotocol:
            message["subprotocol"] = subprotocol
        if headers:
            message["headers"] = [
                (k.encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()
            ]

        await self._send(message)
        self._state = WebSocketState.CONNECTED

    async def close(self, code: int = 1000, reason: str = "") -> None:
        """Close the WebSocket connection.

        Args:
            code: Close code (default 1000 = normal closure).
            reason: Optional close reason.
        """
        if self._state == WebSocketState.DISCONNECTED:
            return

        await self._send(
            {
                "type": "websocket.close",
                "code": code,
                "reason": reason,
            }
        )
        self._state = WebSocketState.DISCONNECTED

    async def receive(self) -> dict[str, Any]:
        """Receive a raw WebSocket message.

        Returns:
            ASGI WebSocket message.

        Raises:
            WebSocketDisconnect: If the client disconnects.
        """
        if self._state == WebSocketState.DISCONNECTED:
            raise WebSocketDisconnect(code=1000)

        message = await self._receive()

        if message["type"] == "websocket.disconnect":
            self._state = WebSocketState.DISCONNECTED
            raise WebSocketDisconnect(
                code=message.get("code", 1000),
                reason=message.get("reason", ""),
            )

        return dict(message)

    async def receive_text(self) -> str:
        """Receive a text message.

        Returns:
            Text message content.

        Raises:
            WebSocketDisconnect: If the client disconnects.
            RuntimeError: If an unexpected message type is received.
        """
        message = await self.receive()
        if message["type"] != "websocket.receive":
            raise RuntimeError(f"Unexpected message type: {message['type']}")

        if "text" in message:
            return str(message["text"])
        elif "bytes" in message:
            return message["bytes"].decode("utf-8")
        else:
            raise RuntimeError("No text or bytes in message")

    async def receive_bytes(self) -> bytes:
        """Receive a binary message.

        Returns:
            Binary message content.

        Raises:
            WebSocketDisconnect: If the client disconnects.
            RuntimeError: If an unexpected message type is received.
        """
        message = await self.receive()
        if message["type"] != "websocket.receive":
            raise RuntimeError(f"Unexpected message type: {message['type']}")

        if "bytes" in message:
            return bytes(message["bytes"])
        elif "text" in message:
            return message["text"].encode("utf-8")
        else:
            raise RuntimeError("No text or bytes in message")

    async def receive_json(self) -> Any:
        """Receive and parse a JSON message.

        Returns:
            Parsed JSON data.

        Raises:
            WebSocketDisconnect: If the client disconnects.
            orjson.JSONDecodeError: If message is not valid JSON.
        """
        text = await self.receive_text()
        return pykour_json.loads(text)

    async def send(self, message: dict[str, Any]) -> None:
        """Send a raw WebSocket message.

        Args:
            message: ASGI WebSocket message.

        Raises:
            RuntimeError: If not connected.
        """
        if self._state != WebSocketState.CONNECTED:
            raise RuntimeError(f"Cannot send in state {self._state.name}")
        await self._send(message)

    async def send_text(self, data: str) -> None:
        """Send a text message.

        Args:
            data: Text content to send.
        """
        await self.send({"type": "websocket.send", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        """Send a binary message.

        Args:
            data: Binary content to send.
        """
        await self.send({"type": "websocket.send", "bytes": data})

    async def send_json(self, data: Any) -> None:
        """Send a JSON message.

        Args:
            data: Data to serialize and send as JSON.
        """
        text = pykour_json.dumps(data).decode("utf-8")
        await self.send_text(text)

    async def iter_text(self) -> AsyncIterator[str]:
        """Iterate over text messages until disconnect.

        Yields:
            Text messages.
        """
        try:
            while True:
                yield await self.receive_text()
        except WebSocketDisconnect:
            pass

    async def iter_bytes(self) -> AsyncIterator[bytes]:
        """Iterate over binary messages until disconnect.

        Yields:
            Binary messages.
        """
        try:
            while True:
                yield await self.receive_bytes()
        except WebSocketDisconnect:
            pass

    async def iter_json(self) -> AsyncIterator[Any]:
        """Iterate over JSON messages until disconnect.

        Yields:
            Parsed JSON data.
        """
        try:
            while True:
                yield await self.receive_json()
        except WebSocketDisconnect:
            pass
