"""WebSocket testing utilities for Pykour applications."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from pykour import json as pykour_json

if TYPE_CHECKING:
    from pykour.types import ASGIApp


class WebSocketTestSessionClosed(Exception):
    """Raised when trying to use a closed WebSocket session."""

    def __init__(self, code: int = 1000, reason: str = "") -> None:
        """Initialize exception.

        Args:
            code: WebSocket close code.
            reason: Close reason.
        """
        self.code = code
        self.reason = reason
        super().__init__(f"WebSocket session closed: code={code}, reason={reason}")


class _WebSocketReceive:
    """ASGI receive callable for WebSocket test session.

    This simulates the client side sending messages to the server.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._connected = False

    def put(self, message: dict[str, Any]) -> None:
        """Add a message to be received by the handler."""
        self._queue.put_nowait(message)

    async def __call__(self) -> dict[str, Any]:
        """Return next message."""
        if not self._connected:
            self._connected = True
            return {"type": "websocket.connect"}

        return await self._queue.get()


class _WebSocketSend:
    """ASGI send callable for WebSocket test session.

    This captures messages sent by the server to the client.
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._accepted = False
        self._closed = False
        self._accept_event = asyncio.Event()

    async def __call__(self, message: dict[str, Any]) -> None:
        """Record sent message."""
        if message["type"] == "websocket.accept":
            self._accepted = True
            self._accept_event.set()
        elif message["type"] == "websocket.close":
            self._closed = True
            await self._queue.put(message)
        elif message["type"] == "websocket.send":
            await self._queue.put(message)

    async def get(self, timeout: float = 5.0) -> dict[str, Any]:
        """Get next message from server."""
        try:
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except asyncio.TimeoutError as e:
            raise TimeoutError("Timeout waiting for WebSocket message") from e


class WebSocketTestSession:
    """WebSocket test session for testing WebSocket handlers.

    Provides methods to send and receive WebSocket messages during tests.

    Example:
        async with client.websocket_connect("/ws/chat") as ws:
            await ws.send_text("Hello")
            response = await ws.receive_text()
            assert response == "Echo: Hello"
    """

    def __init__(
        self,
        app: ASGIApp,
        path: str,
        headers: dict[str, str] | None = None,
        subprotocols: list[str] | None = None,
    ) -> None:
        """Initialize WebSocket test session.

        Args:
            app: The ASGI application.
            path: WebSocket path.
            headers: Optional connection headers.
            subprotocols: Optional list of subprotocols.
        """
        self._app = app
        self._path = path
        self._headers = headers or {}
        self._subprotocols = subprotocols or []

        self._receive = _WebSocketReceive()
        self._send = _WebSocketSend()

        self._task: asyncio.Task[None] | None = None
        self._closed = False

    async def __aenter__(self) -> "WebSocketTestSession":
        """Enter async context and connect."""
        await self._connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context and close."""
        await self.close()

    async def _connect(self) -> None:
        """Establish WebSocket connection."""
        scope = self._build_scope()

        # Run handler in background
        coro = self._app(scope, self._receive, self._send)  # type: ignore[arg-type]
        self._task = asyncio.create_task(coro)  # type: ignore[arg-type]

        # Wait for accept (with timeout)
        try:
            await asyncio.wait_for(self._send._accept_event.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            if self._task:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            raise RuntimeError("WebSocket connection was not accepted")

    def _build_scope(self) -> dict[str, Any]:
        """Build WebSocket ASGI scope."""
        header_list: list[tuple[bytes, bytes]] = [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in self._headers.items()
        ]
        if not any(k == b"host" for k, _ in header_list):
            header_list.append((b"host", b"testserver"))

        return {
            "type": "websocket",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "path": self._path,
            "root_path": "",
            "query_string": b"",
            "headers": header_list,
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "subprotocols": self._subprotocols,
        }

    @property
    def accepted_subprotocol(self) -> str | None:
        """Get the accepted subprotocol.

        Returns:
            Accepted subprotocol or None if not accepted yet.
        """
        # The subprotocol is returned in the accept message
        return None  # Would need to capture from accept message

    async def send(self, message: dict[str, Any]) -> None:
        """Send raw WebSocket message to server.

        Args:
            message: ASGI WebSocket receive message.

        Raises:
            WebSocketTestSessionClosed: If session is closed.
        """
        if self._closed:
            raise WebSocketTestSessionClosed()
        self._receive.put(message)
        # Give handler time to process
        await asyncio.sleep(0)

    async def send_text(self, data: str) -> None:
        """Send text message to server.

        Args:
            data: Text content to send.
        """
        await self.send({"type": "websocket.receive", "text": data})

    async def send_bytes(self, data: bytes) -> None:
        """Send binary message to server.

        Args:
            data: Binary content to send.
        """
        await self.send({"type": "websocket.receive", "bytes": data})

    async def send_json(self, data: Any) -> None:
        """Send JSON message to server.

        Args:
            data: Data to serialize and send as JSON.
        """
        text = pykour_json.dumps(data).decode("utf-8")
        await self.send_text(text)

    async def receive(self, timeout: float = 5.0) -> dict[str, Any]:
        """Receive raw WebSocket message from server.

        Args:
            timeout: Timeout in seconds.

        Returns:
            ASGI WebSocket send message.

        Raises:
            WebSocketTestSessionClosed: If session is closed.
            TimeoutError: If no message received within timeout.
        """
        if self._closed:
            raise WebSocketTestSessionClosed()

        msg = await self._send.get(timeout=timeout)

        if msg["type"] == "websocket.close":
            self._closed = True
            raise WebSocketTestSessionClosed(
                code=msg.get("code", 1000),
                reason=msg.get("reason", ""),
            )

        return msg

    async def receive_text(self, timeout: float = 5.0) -> str:
        """Receive text message from server.

        Args:
            timeout: Timeout in seconds.

        Returns:
            Text content.

        Raises:
            WebSocketTestSessionClosed: If session is closed.
            TimeoutError: If no message received within timeout.
        """
        msg = await self.receive(timeout=timeout)
        if "text" in msg:
            return str(msg["text"])
        elif "bytes" in msg:
            return msg["bytes"].decode("utf-8")
        raise RuntimeError("No text in message")

    async def receive_bytes(self, timeout: float = 5.0) -> bytes:
        """Receive binary message from server.

        Args:
            timeout: Timeout in seconds.

        Returns:
            Binary content.

        Raises:
            WebSocketTestSessionClosed: If session is closed.
            TimeoutError: If no message received within timeout.
        """
        msg = await self.receive(timeout=timeout)
        if "bytes" in msg:
            return bytes(msg["bytes"])
        elif "text" in msg:
            return msg["text"].encode("utf-8")
        raise RuntimeError("No bytes in message")

    async def receive_json(self, timeout: float = 5.0) -> Any:
        """Receive and parse JSON message from server.

        Args:
            timeout: Timeout in seconds.

        Returns:
            Parsed JSON data.

        Raises:
            WebSocketTestSessionClosed: If session is closed.
            TimeoutError: If no message received within timeout.
        """
        text = await self.receive_text(timeout=timeout)
        return pykour_json.loads(text)

    async def close(self, code: int = 1000) -> None:
        """Close the WebSocket connection.

        Args:
            code: Close code (default 1000 = normal closure).
        """
        if self._closed:
            return

        # Send disconnect message to handler
        self._receive.put(
            {
                "type": "websocket.disconnect",
                "code": code,
            }
        )

        self._closed = True

        # Wait for task to complete
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=1.0)
            except asyncio.TimeoutError:
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
            except Exception:
                pass
