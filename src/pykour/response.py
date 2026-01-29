"""HTTP Response classes for ASGI."""

from __future__ import annotations

import mimetypes
from collections.abc import AsyncIterable, Iterable
from dataclasses import dataclass
from pathlib import Path as FilePath
from typing import Any

import aiofiles

from pykour import json as pykour_json
from pykour.types import Receive, Scope, Send

# Type alias for streaming content
ContentStream = (
    AsyncIterable[bytes] | AsyncIterable[str] | Iterable[bytes] | Iterable[str]
)


def is_body_allowed_for_status_code(status_code: int) -> bool:
    """Check if HTTP status code allows a response body.

    Per RFC 7230/7231:
    - 1xx (Informational): No body allowed
    - 204 (No Content): No body allowed
    - 304 (Not Modified): No body allowed

    Args:
        status_code: HTTP status code to check.

    Returns:
        True if body is allowed, False otherwise.
    """
    if status_code < 200:  # 1xx
        return False
    if status_code in (204, 304):
        return False
    return True


class Response:
    """Base HTTP response."""

    def __init__(
        self,
        content: bytes | str = b"",
        status_code: int = 200,
        headers: dict[str, str] | list[tuple[str, str]] | None = None,
        media_type: str | None = None,
    ) -> None:
        self.status_code = status_code
        self.media_type = media_type

        # Store headers as list of tuples to preserve duplicates
        if headers is None:
            self._headers: list[tuple[str, str]] = []
        elif isinstance(headers, dict):
            self._headers = list(headers.items())
        else:
            self._headers = list(headers)

        if isinstance(content, str):
            self.body = content.encode("utf-8")
        else:
            self.body = content

    @property
    def headers(self) -> list[tuple[str, str]]:
        """Response headers as list of tuples (preserves duplicates)."""
        return self._headers

    def set_cookie(
        self,
        name: str,
        value: str,
        *,
        max_age: int | None = None,
        expires: str | None = None,
        path: str = "/",
        domain: str | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str | None = "Lax",
    ) -> None:
        """Set a cookie in the response.

        Args:
            name: Cookie name.
            value: Cookie value.
            max_age: Max age in seconds.
            expires: Expiration date string (GMT format).
            path: Cookie path.
            domain: Cookie domain.
            secure: Secure flag (HTTPS only).
            httponly: HttpOnly flag (no JavaScript access).
            samesite: SameSite policy ("Strict", "Lax", "None").

        Example:
            response.set_cookie("session_id", "abc123", httponly=True, secure=True)
        """
        cookie_parts = [f"{name}={value}"]

        if max_age is not None:
            cookie_parts.append(f"Max-Age={max_age}")
        if expires is not None:
            cookie_parts.append(f"Expires={expires}")
        if path:
            cookie_parts.append(f"Path={path}")
        if domain:
            cookie_parts.append(f"Domain={domain}")
        if secure:
            cookie_parts.append("Secure")
        if httponly:
            cookie_parts.append("HttpOnly")
        if samesite:
            cookie_parts.append(f"SameSite={samesite}")

        cookie_value = "; ".join(cookie_parts)
        self._headers.append(("Set-Cookie", cookie_value))

    def delete_cookie(
        self,
        name: str,
        *,
        path: str = "/",
        domain: str | None = None,
    ) -> None:
        """Delete a cookie by setting it to expire immediately.

        Args:
            name: Cookie name to delete.
            path: Cookie path.
            domain: Cookie domain.

        Example:
            response.delete_cookie("session_id")
        """
        self.set_cookie(
            name,
            "",
            max_age=0,
            path=path,
            domain=domain,
            samesite=None,
        )

    def add_header(self, name: str, value: str) -> None:
        """Add a header to the response.

        Allows duplicate headers (important for Set-Cookie, etc.).

        Args:
            name: Header name (e.g., "X-Custom-Header", "Cache-Control").
            value: Header value.

        Example:
            response.add_header("X-Request-Id", request_id)
            response.add_header("Cache-Control", "max-age=3600")
        """
        self._headers.append((name, value))

    def set_header(self, name: str, value: str) -> None:
        """Set a header, replacing any existing header with the same name.

        Use this when you want only one header with this name.
        For headers that can have multiple values (Set-Cookie), use add_header().

        Args:
            name: Header name.
            value: Header value.

        Example:
            response.set_header("X-Version", "2.0")  # Replaces any existing X-Version
        """
        # Remove existing headers with same name (case-insensitive)
        self._headers = [(k, v) for k, v in self._headers if k.lower() != name.lower()]
        self._headers.append((name, value))

    def get_header(self, name: str) -> str | None:
        """Get first header value by name (case-insensitive).

        Args:
            name: Header name to look up.

        Returns:
            Header value or None if not found.

        Example:
            content_type = response.get_header("Content-Type")
        """
        name_lower = name.lower()
        for k, v in self._headers:
            if k.lower() == name_lower:
                return v
        return None

    def remove_header(self, name: str) -> bool:
        """Remove all headers with the given name.

        Args:
            name: Header name to remove.

        Returns:
            True if any headers were removed, False otherwise.

        Example:
            response.remove_header("X-Debug")
        """
        name_lower = name.lower()
        original_len = len(self._headers)
        self._headers = [(k, v) for k, v in self._headers if k.lower() != name_lower]
        return len(self._headers) < original_len

    def _build_headers(self) -> list[tuple[bytes, bytes]]:
        """Build ASGI-compatible headers list.

        Auto-generated headers (content-type from media_type, content-length from body)
        take precedence over user-provided headers to ensure correctness.
        User-provided content-type and content-length headers are filtered out.

        Per RFC 7230/7231, Content-Type and Content-Length are not included for
        status codes that do not allow a body (1xx, 204, 304).
        """
        # Reserved headers that are auto-generated (case-insensitive)
        reserved_headers = {"content-type", "content-length"}

        headers: list[tuple[bytes, bytes]] = []

        # Only include Content-Type and Content-Length for status codes that allow body
        if is_body_allowed_for_status_code(self.status_code):
            if self.media_type is not None:
                headers.append((b"content-type", self.media_type.encode("latin-1")))

            headers.append((b"content-length", str(len(self.body)).encode("latin-1")))

        # Append user headers, filtering out reserved ones
        for key, value in self._headers:
            if key.lower() not in reserved_headers:
                headers.append((key.encode("latin-1"), value.encode("latin-1")))

        return headers

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Send the response via ASGI.

        Args:
            scope: ASGI scope (unused, for ASGI compatibility).
            receive: ASGI receive callable (unused, for ASGI compatibility).
            send: ASGI send callable.
        """
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self._build_headers(),
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": self.body,
            }
        )


class JSONResponse(Response):
    """JSON response."""

    def __init__(
        self,
        content: Any = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        # orjson returns bytes directly
        body = pykour_json.dumps(content)
        super().__init__(
            content=body,
            status_code=status_code,
            headers=headers,
            media_type="application/json",
        )


class HTMLResponse(Response):
    """HTML response."""

    def __init__(
        self,
        content: bytes | str = "",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/html; charset=utf-8",
        )


class PlainTextResponse(Response):
    """Plain text response."""

    def __init__(
        self,
        content: bytes | str = "",
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(
            content=content,
            status_code=status_code,
            headers=headers,
            media_type="text/plain; charset=utf-8",
        )


class FileResponse(Response):
    """File response that streams file content in chunks.

    Example:
        ```python
        from pykour import FileResponse

        async def get() -> FileResponse:
            return FileResponse("/path/to/file.pdf")

        # With download filename
        async def get_download() -> FileResponse:
            return FileResponse(
                "/path/to/report.pdf",
                filename="monthly_report.pdf"
            )
        ```
    """

    DEFAULT_CHUNK_SIZE = 64 * 1024  # 64KB

    def __init__(
        self,
        path: str | FilePath,
        *,
        status_code: int = 200,
        headers: dict[str, str] | list[tuple[str, str]] | None = None,
        media_type: str | None = None,
        filename: str | None = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> None:
        """Initialize FileResponse.

        Args:
            path: Path to the file to serve.
            status_code: HTTP status code (default 200).
            headers: Additional response headers.
            media_type: Content-Type (auto-detected if not provided).
            filename: Optional download filename for Content-Disposition.
            chunk_size: Size of chunks for streaming (default 64KB).

        Raises:
            FileNotFoundError: If the file does not exist.
            IsADirectoryError: If the path is a directory.
        """
        self.path = FilePath(path)
        self.chunk_size = chunk_size
        self.filename = filename

        # Validate file exists
        if not self.path.exists():
            raise FileNotFoundError(f"File not found: {self.path}")
        if self.path.is_dir():
            raise IsADirectoryError(f"Path is a directory: {self.path}")

        # Get file stats
        self.file_size = self.path.stat().st_size

        # Auto-detect media type
        if media_type is None:
            guessed_type, _ = mimetypes.guess_type(str(self.path))
            media_type = guessed_type or "application/octet-stream"

        # Initialize base Response (empty body, headers will be built separately)
        super().__init__(
            content=b"",
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )

    def _build_headers(self) -> list[tuple[bytes, bytes]]:
        """Build headers including Content-Length and Content-Disposition."""
        headers: list[tuple[bytes, bytes]] = []

        # Content-Type
        if self.media_type is not None:
            headers.append((b"content-type", self.media_type.encode("latin-1")))

        # Content-Length (from file size, not body)
        headers.append((b"content-length", str(self.file_size).encode("latin-1")))

        # Content-Disposition for downloads
        if self.filename:
            disposition = f'attachment; filename="{self.filename}"'
            headers.append((b"content-disposition", disposition.encode("latin-1")))

        # User headers (excluding reserved)
        reserved_headers = {"content-type", "content-length", "content-disposition"}
        for key, value in self._headers:
            if key.lower() not in reserved_headers:
                headers.append((key.encode("latin-1"), value.encode("latin-1")))

        return headers

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Send the file response via ASGI with chunked streaming.

        Uses aiofiles for async I/O when available, otherwise falls back
        to synchronous file reading.
        """
        # Send headers
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self._build_headers(),
            }
        )

        # Handle empty file
        if self.file_size == 0:
            await send(
                {
                    "type": "http.response.body",
                    "body": b"",
                    "more_body": False,
                }
            )
            return

        # Stream file in chunks using async I/O
        async with aiofiles.open(self.path, "rb") as f:
            bytes_sent = 0
            while True:
                chunk = await f.read(self.chunk_size)
                bytes_sent += len(chunk)
                more_body = bytes_sent < self.file_size

                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": more_body,
                    }
                )

                if not more_body:
                    break


class StreamingResponse(Response):
    """Streaming response that sends content from an async generator.

    Useful for streaming large responses, real-time data, or chunked transfers.

    Example:
        ```python
        from pykour import StreamingResponse

        async def generate_data():
            for i in range(100):
                yield f"chunk {i}\\n".encode()
                await asyncio.sleep(0.1)

        async def get() -> StreamingResponse:
            return StreamingResponse(
                generate_data(),
                media_type="text/plain",
            )
        ```
    """

    def __init__(
        self,
        content: ContentStream,
        status_code: int = 200,
        headers: dict[str, str] | list[tuple[str, str]] | None = None,
        media_type: str | None = None,
    ) -> None:
        """Initialize StreamingResponse.

        Args:
            content: Async iterable or iterable yielding bytes or str.
            status_code: HTTP status code (default 200).
            headers: Additional response headers.
            media_type: Content-Type header value.
        """
        super().__init__(
            content=b"",
            status_code=status_code,
            headers=headers,
            media_type=media_type,
        )
        self._content_iterator = content

    def _build_headers(self) -> list[tuple[bytes, bytes]]:
        """Build headers for streaming response.

        Note: Content-Length is NOT included for streaming responses
        as the total size is unknown upfront.
        """
        headers: list[tuple[bytes, bytes]] = []

        if self.media_type is not None:
            headers.append((b"content-type", self.media_type.encode("latin-1")))

        # Don't include content-length for streaming
        reserved_headers = {"content-type", "content-length"}
        for key, value in self._headers:
            if key.lower() not in reserved_headers:
                headers.append((key.encode("latin-1"), value.encode("latin-1")))

        return headers

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Send the streaming response via ASGI."""
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self._build_headers(),
            }
        )

        # Stream content from iterator
        async for chunk in self._iterate_content():
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")

            await send(
                {
                    "type": "http.response.body",
                    "body": chunk,
                    "more_body": True,
                }
            )

        # Final empty body to signal completion
        await send(
            {
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            }
        )

    async def _iterate_content(self) -> AsyncIterable[bytes | str]:
        """Iterate over content, handling both sync and async iterables."""
        if hasattr(self._content_iterator, "__aiter__"):
            # Async iterable - cast to help type checker
            async_iter: AsyncIterable[bytes | str] = self._content_iterator  # type: ignore[assignment]
            async for chunk in async_iter:
                yield chunk
        else:
            # Sync iterable - cast to help type checker
            sync_iter: Iterable[bytes | str] = self._content_iterator
            for chunk in sync_iter:
                yield chunk


@dataclass
class ServerSentEvent:
    """Server-Sent Event data structure.

    Attributes:
        data: Event data (will be JSON-encoded if not a string).
        event: Event type/name.
        id: Event ID for client tracking.
        retry: Reconnection time in milliseconds.

    Example:
        ```python
        event = ServerSentEvent(
            data={"count": 42},
            event="update",
            id="msg-1",
        )
        ```
    """

    data: Any
    event: str | None = None
    id: str | None = None
    retry: int | None = None

    def encode(self) -> bytes:
        """Encode event to SSE wire format.

        Returns:
            Bytes in SSE format (e.g., "event: update\\ndata: {...}\\n\\n").
        """
        lines: list[str] = []

        if self.event is not None:
            lines.append(f"event: {self.event}")

        if self.id is not None:
            lines.append(f"id: {self.id}")

        if self.retry is not None:
            lines.append(f"retry: {self.retry}")

        # Handle data - can be string or any JSON-serializable type
        if isinstance(self.data, str):
            data_str = self.data
        else:
            data_str = pykour_json.dumps(self.data).decode("utf-8")

        # Split data by newlines (SSE spec: each line prefixed with "data:")
        for line in data_str.split("\n"):
            lines.append(f"data: {line}")

        # SSE events are terminated with double newline
        return ("\n".join(lines) + "\n\n").encode("utf-8")


class EventSourceResponse(Response):
    """Server-Sent Events (SSE) response for real-time streaming.

    Automatically sets the correct Content-Type and handles
    event formatting according to the SSE specification.

    Example:
        ```python
        from pykour import EventSourceResponse, ServerSentEvent

        async def event_stream():
            for i in range(10):
                yield ServerSentEvent(
                    data={"count": i},
                    event="update",
                    id=str(i),
                )
                await asyncio.sleep(1)

        async def get() -> EventSourceResponse:
            return EventSourceResponse(event_stream())
        ```

    Simple string events:
        ```python
        async def simple_stream():
            yield "First message"
            await asyncio.sleep(1)
            yield "Second message"

        async def get() -> EventSourceResponse:
            return EventSourceResponse(simple_stream())
        ```
    """

    SSE_MEDIA_TYPE = "text/event-stream"

    def __init__(
        self,
        content: AsyncIterable[ServerSentEvent | str | dict[str, Any]],
        status_code: int = 200,
        headers: dict[str, str] | list[tuple[str, str]] | None = None,
    ) -> None:
        """Initialize EventSourceResponse.

        Args:
            content: Async iterable yielding SSE events, strings, or dicts.
            status_code: HTTP status code (default 200).
            headers: Additional response headers.
        """
        super().__init__(
            content=b"",
            status_code=status_code,
            headers=headers,
            media_type=self.SSE_MEDIA_TYPE,
        )
        self._content_iterator = content

    def _build_headers(self) -> list[tuple[bytes, bytes]]:
        """Build headers for SSE response."""
        headers: list[tuple[bytes, bytes]] = [
            (b"content-type", self.SSE_MEDIA_TYPE.encode("latin-1")),
            (b"cache-control", b"no-cache"),
            (b"connection", b"keep-alive"),
        ]

        reserved_headers = {
            "content-type",
            "content-length",
            "cache-control",
            "connection",
        }
        for key, value in self._headers:
            if key.lower() not in reserved_headers:
                headers.append((key.encode("latin-1"), value.encode("latin-1")))

        return headers

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Send the SSE response via ASGI."""
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self._build_headers(),
            }
        )

        # Stream events
        async for event in self._content_iterator:
            encoded = self._encode_event(event)

            await send(
                {
                    "type": "http.response.body",
                    "body": encoded,
                    "more_body": True,
                }
            )

        # Final empty body
        await send(
            {
                "type": "http.response.body",
                "body": b"",
                "more_body": False,
            }
        )

    def _encode_event(self, event: ServerSentEvent | str | dict[str, Any]) -> bytes:
        """Encode an event to SSE wire format."""
        if isinstance(event, ServerSentEvent):
            return event.encode()
        elif isinstance(event, str):
            return ServerSentEvent(data=event).encode()
        elif isinstance(event, dict):
            return ServerSentEvent(data=event).encode()
        else:
            return ServerSentEvent(data=event).encode()
