"""Tests for WebSocket support."""

import pytest

from pykour.websocket import WebSocket, WebSocketDisconnect, WebSocketState


class MockReceive:
    """Mock receive callable for testing."""

    def __init__(self) -> None:
        self.messages: list[dict] = []
        self._index = 0

    def add_message(self, message: dict) -> None:
        """Add a message to be received."""
        self.messages.append(message)

    async def __call__(self) -> dict:
        """Return next message or disconnect."""
        if self._index < len(self.messages):
            message = self.messages[self._index]
            self._index += 1
            return message
        return {"type": "websocket.disconnect", "code": 1000}


class MockSend:
    """Mock send callable for testing."""

    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def __call__(self, message: dict) -> None:
        """Record sent message."""
        self.messages.append(message)


def create_ws_scope(
    path: str = "/ws",
    query_string: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> dict:
    """Create a WebSocket ASGI scope."""
    return {
        "type": "websocket",
        "path": path,
        "query_string": query_string,
        "headers": headers or [(b"host", b"localhost")],
        "client": ("127.0.0.1", 50000),
    }


class TestWebSocketBasic:
    """Tests for WebSocket class."""

    @pytest.mark.asyncio
    async def test_websocket_accept(self) -> None:
        """WebSocket.accept() should send accept message."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)

        assert ws.state == WebSocketState.CONNECTING

        await ws.accept()

        assert ws.state == WebSocketState.CONNECTED
        assert send.messages[-1]["type"] == "websocket.accept"

    @pytest.mark.asyncio
    async def test_websocket_accept_with_subprotocol(self) -> None:
        """WebSocket.accept() should include subprotocol."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)

        await ws.accept(subprotocol="graphql")

        assert send.messages[-1]["subprotocol"] == "graphql"

    @pytest.mark.asyncio
    async def test_websocket_accept_with_headers(self) -> None:
        """WebSocket.accept() should include custom headers."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)

        await ws.accept(headers={"X-Custom": "value"})

        assert send.messages[-1]["headers"] == [(b"X-Custom", b"value")]

    @pytest.mark.asyncio
    async def test_websocket_send_text(self) -> None:
        """WebSocket.send_text() should send text message."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        await ws.send_text("hello")

        assert send.messages[-1] == {
            "type": "websocket.send",
            "text": "hello",
        }

    @pytest.mark.asyncio
    async def test_websocket_send_bytes(self) -> None:
        """WebSocket.send_bytes() should send binary message."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        await ws.send_bytes(b"\x00\x01\x02")

        assert send.messages[-1] == {
            "type": "websocket.send",
            "bytes": b"\x00\x01\x02",
        }

    @pytest.mark.asyncio
    async def test_websocket_send_json(self) -> None:
        """WebSocket.send_json() should send JSON message."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        await ws.send_json({"key": "value"})

        assert send.messages[-1]["type"] == "websocket.send"
        assert "text" in send.messages[-1]
        assert '"key"' in send.messages[-1]["text"]

    @pytest.mark.asyncio
    async def test_websocket_receive_text(self) -> None:
        """WebSocket.receive_text() should receive text message."""
        receive = MockReceive()
        receive.add_message(
            {
                "type": "websocket.receive",
                "text": "hello",
            }
        )

        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        text = await ws.receive_text()
        assert text == "hello"

    @pytest.mark.asyncio
    async def test_websocket_receive_bytes(self) -> None:
        """WebSocket.receive_bytes() should receive binary message."""
        receive = MockReceive()
        receive.add_message(
            {
                "type": "websocket.receive",
                "bytes": b"\x00\x01\x02",
            }
        )

        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        data = await ws.receive_bytes()
        assert data == b"\x00\x01\x02"

    @pytest.mark.asyncio
    async def test_websocket_receive_json(self) -> None:
        """WebSocket.receive_json() should receive and parse JSON."""
        receive = MockReceive()
        receive.add_message(
            {
                "type": "websocket.receive",
                "text": '{"key": "value"}',
            }
        )

        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        data = await ws.receive_json()
        assert data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_websocket_disconnect_raises(self) -> None:
        """WebSocket should raise WebSocketDisconnect on disconnect."""
        receive = MockReceive()
        receive.add_message(
            {
                "type": "websocket.disconnect",
                "code": 1001,
            }
        )

        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await ws.receive_text()

        assert exc_info.value.code == 1001

    @pytest.mark.asyncio
    async def test_websocket_close(self) -> None:
        """WebSocket.close() should send close message."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        await ws.close(code=1000, reason="bye")

        assert ws.state == WebSocketState.DISCONNECTED
        assert send.messages[-1] == {
            "type": "websocket.close",
            "code": 1000,
            "reason": "bye",
        }

    @pytest.mark.asyncio
    async def test_websocket_close_idempotent(self) -> None:
        """WebSocket.close() should be idempotent."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        await ws.close()
        await ws.close()  # Second call should not raise

        # Only one close message
        close_messages = [m for m in send.messages if m["type"] == "websocket.close"]
        assert len(close_messages) == 1


class TestWebSocketProperties:
    """Tests for WebSocket properties."""

    def test_websocket_path(self) -> None:
        """WebSocket.path should return the path."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(path="/ws/chat"), receive, send)

        assert ws.path == "/ws/chat"

    def test_websocket_path_params(self) -> None:
        """WebSocket.path_params should return path parameters."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send, {"room": "general"})

        assert ws.path_params == {"room": "general"}

    def test_websocket_query_params(self) -> None:
        """WebSocket.query_params should return query parameters."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(
            create_ws_scope(query_string=b"token=abc&page=1"),
            receive,
            send,
        )

        assert ws.query_params == {"token": "abc", "page": "1"}

    def test_websocket_headers(self) -> None:
        """WebSocket.headers should return headers."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(
            create_ws_scope(headers=[(b"host", b"example.com"), (b"x-custom", b"val")]),
            receive,
            send,
        )

        assert ws.headers["host"] == "example.com"
        assert ws.headers["x-custom"] == "val"

    def test_websocket_client(self) -> None:
        """WebSocket.client should return client address."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)

        assert ws.client == ("127.0.0.1", 50000)


class TestWebSocketIterators:
    """Tests for WebSocket iterator methods."""

    @pytest.mark.asyncio
    async def test_iter_text(self) -> None:
        """WebSocket.iter_text() should iterate until disconnect."""
        receive = MockReceive()
        receive.add_message({"type": "websocket.receive", "text": "msg1"})
        receive.add_message({"type": "websocket.receive", "text": "msg2"})
        # Disconnect will be returned automatically

        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        messages = []
        async for msg in ws.iter_text():
            messages.append(msg)

        assert messages == ["msg1", "msg2"]

    @pytest.mark.asyncio
    async def test_iter_bytes(self) -> None:
        """WebSocket.iter_bytes() should iterate until disconnect."""
        receive = MockReceive()
        receive.add_message({"type": "websocket.receive", "bytes": b"data1"})
        receive.add_message({"type": "websocket.receive", "bytes": b"data2"})

        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        messages = []
        async for msg in ws.iter_bytes():
            messages.append(msg)

        assert messages == [b"data1", b"data2"]

    @pytest.mark.asyncio
    async def test_iter_json(self) -> None:
        """WebSocket.iter_json() should iterate JSON messages until disconnect."""
        receive = MockReceive()
        receive.add_message({"type": "websocket.receive", "text": '{"n": 1}'})
        receive.add_message({"type": "websocket.receive", "text": '{"n": 2}'})

        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()

        messages = []
        async for msg in ws.iter_json():
            messages.append(msg)

        assert messages == [{"n": 1}, {"n": 2}]


class TestWebSocketErrors:
    """Tests for WebSocket error handling."""

    @pytest.mark.asyncio
    async def test_accept_twice_raises(self) -> None:
        """WebSocket.accept() should raise if already connected."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)

        await ws.accept()

        with pytest.raises(RuntimeError, match="Cannot accept"):
            await ws.accept()

    @pytest.mark.asyncio
    async def test_send_before_accept_raises(self) -> None:
        """WebSocket.send_text() should raise if not connected."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)

        with pytest.raises(RuntimeError, match="Cannot send"):
            await ws.send_text("hello")

    @pytest.mark.asyncio
    async def test_receive_after_disconnect_raises(self) -> None:
        """WebSocket.receive_text() should raise if disconnected."""
        receive = MockReceive()
        send = MockSend()
        ws = WebSocket(create_ws_scope(), receive, send)
        await ws.accept()
        await ws.close()

        with pytest.raises(WebSocketDisconnect):
            await ws.receive_text()


class TestWebSocketExport:
    """Tests for WebSocket exports."""

    def test_websocket_exported_from_pykour(self) -> None:
        """WebSocket should be exported from pykour package."""
        from pykour import WebSocket as ExportedWebSocket

        assert ExportedWebSocket is WebSocket

    def test_websocket_disconnect_exported_from_pykour(self) -> None:
        """WebSocketDisconnect should be exported from pykour package."""
        from pykour import WebSocketDisconnect as ExportedWebSocketDisconnect

        assert ExportedWebSocketDisconnect is WebSocketDisconnect

    def test_websocket_state_exported_from_pykour(self) -> None:
        """WebSocketState should be exported from pykour package."""
        from pykour import WebSocketState as ExportedWebSocketState

        assert ExportedWebSocketState is WebSocketState
