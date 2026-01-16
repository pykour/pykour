"""Helper functions for tests."""

from __future__ import annotations

from typing import Any

from pykour.types import Message, Scope


def create_scope(
    method: str = "GET",
    path: str = "/",
    query_string: bytes = b"",
    headers: list[tuple[bytes, bytes]] | None = None,
    scheme: str = "http",
    server: tuple[str, int] = ("127.0.0.1", 8000),
    http_version: str = "1.1",
    **extra: Any,
) -> Scope:
    """Create a test HTTP ASGI scope.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        query_string: URL query string as bytes
        headers: List of header tuples (name, value) as bytes
        scheme: URL scheme (http or https)
        server: Server tuple (host, port)
        http_version: HTTP version string
        **extra: Additional scope keys

    Returns:
        ASGI HTTP scope dictionary
    """
    scope: Scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string,
        "headers": headers or [],
        "scheme": scheme,
        "server": server,
        "http_version": http_version,
    }
    scope.update(extra)
    return scope


def create_receive(body: bytes = b""):
    """Create a receive callable that returns the given body.

    Args:
        body: Request body content

    Returns:
        Async receive callable
    """
    called = False

    async def receive() -> Message:
        nonlocal called
        if not called:
            called = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    return receive


def create_noop_receive():
    """Create a receive callable that returns disconnect immediately.

    Use this when the receive function won't be called but a typed
    callable is needed.

    Returns:
        Async receive callable
    """

    async def receive() -> Message:
        return {"type": "http.disconnect"}

    return receive


def create_noop_send():
    """Create a send callable that does nothing.

    Use this when the send function won't be called but a typed
    callable is needed.

    Returns:
        Async send callable
    """

    async def send(message: Message) -> None:
        pass

    return send


class MockSend:
    """Mock ASGI send callable for testing."""

    def __init__(self) -> None:
        self.messages: list[Message] = []

    async def __call__(self, message: Message) -> None:
        """Capture sent ASGI message."""
        self.messages.append(message)

    @property
    def status(self) -> int:
        """Get response status code."""
        return self.messages[0]["status"]

    @property
    def body(self) -> bytes:
        """Get response body."""
        return self.messages[1]["body"]

    @property
    def headers(self) -> dict[bytes, bytes]:
        """Get response headers as dict."""
        return dict(self.messages[0]["headers"])

    @property
    def json_body(self) -> Any:
        """Get response body parsed as JSON."""
        import json

        return json.loads(self.body)
