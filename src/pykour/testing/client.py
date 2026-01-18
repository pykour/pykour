"""Test client for Pykour applications."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from pykour.testing.cookies import CookieJar
from pykour.types import Message

if TYPE_CHECKING:
    from pykour.testing.websocket import WebSocketTestSession
    from pykour.types import ASGIApp


@dataclass
class TestResponse:
    __test__ = False  # Prevent pytest from collecting this class
    """Response object returned by TestClient.

    Attributes:
        status_code: HTTP status code.
        headers: Response headers as a dictionary (lowercase keys).
        body: Raw response body bytes.
        raw_headers: Raw headers as list of tuples (preserves duplicates).
    """

    status_code: int
    headers: dict[str, str]
    body: bytes
    raw_headers: list[tuple[str, str]] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Get response body as text."""
        return self.body.decode("utf-8")

    def json(self) -> Any:
        """Parse response body as JSON.

        Returns:
            Parsed JSON data.

        Raises:
            json.JSONDecodeError: If body is not valid JSON.
        """
        return json.loads(self.body)

    @property
    def is_success(self) -> bool:
        """Check if response is successful (2xx status)."""
        return 200 <= self.status_code < 300

    @property
    def is_redirect(self) -> bool:
        """Check if response is a redirect (3xx status)."""
        return 300 <= self.status_code < 400

    @property
    def is_client_error(self) -> bool:
        """Check if response is a client error (4xx status)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response is a server error (5xx status)."""
        return 500 <= self.status_code < 600

    def get_header(self, name: str, default: str | None = None) -> str | None:
        """Get header value by name (case-insensitive).

        Args:
            name: Header name.
            default: Default value if header not found.

        Returns:
            Header value or default.
        """
        return self.headers.get(name.lower(), default)

    @property
    def cookies(self) -> dict[str, str]:
        """Parse Set-Cookie headers into a dict.

        Returns:
            Dictionary mapping cookie names to values.
        """
        result: dict[str, str] = {}
        for key, value in self.raw_headers:
            if key.lower() == "set-cookie":
                name_value = value.split(";")[0].strip()
                if "=" in name_value:
                    name, _, val = name_value.partition("=")
                    result[name.strip()] = val.strip()
        return result

    @property
    def etag(self) -> str | None:
        """Get ETag header value.

        Returns:
            ETag value or None if not present.
        """
        return self.get_header("etag")

    @property
    def last_modified(self) -> str | None:
        """Get Last-Modified header value.

        Returns:
            Last-Modified value or None if not present.
        """
        return self.get_header("last-modified")

    @property
    def cache_control(self) -> dict[str, str | bool]:
        """Parse Cache-Control header into a dict.

        Returns:
            Dictionary with cache control directives.

        Example:
            {"max-age": "3600", "no-cache": True, "private": True}
        """
        header = self.get_header("cache-control")
        if not header:
            return {}

        result: dict[str, str | bool] = {}
        for directive in header.split(","):
            directive = directive.strip()
            if "=" in directive:
                key, _, value = directive.partition("=")
                result[key.strip().lower()] = value.strip().strip('"')
            else:
                result[directive.lower()] = True
        return result

    def assert_status(self, expected: int) -> "TestResponse":
        """Assert status code matches expected value.

        Args:
            expected: Expected status code.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If status code doesn't match.
        """
        assert self.status_code == expected, (
            f"Expected status {expected}, got {self.status_code}"
        )
        return self

    def assert_header(self, name: str, value: str | None = None) -> "TestResponse":
        """Assert header exists and optionally matches value.

        Args:
            name: Header name (case-insensitive).
            value: Expected value (None to just check existence).

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If header doesn't exist or value doesn't match.
        """
        actual = self.get_header(name)
        if value is None:
            assert actual is not None, f"Header '{name}' not found"
        else:
            assert actual == value, (
                f"Header '{name}': expected '{value}', got '{actual}'"
            )
        return self

    def assert_json_equals(self, expected: Any) -> "TestResponse":
        """Assert JSON body equals expected value.

        Args:
            expected: Expected JSON data.

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If JSON body doesn't match.
        """
        assert self.json() == expected
        return self

    def assert_json_contains(
        self, key: str, value: Any | None = None
    ) -> "TestResponse":
        """Assert JSON body contains key and optionally matches value.

        Args:
            key: Key to check (supports dot notation for nested keys).
            value: Expected value (None to just check existence).

        Returns:
            Self for method chaining.

        Raises:
            AssertionError: If key not found or value doesn't match.
        """
        data = self.json()
        keys = key.split(".")
        for k in keys:
            assert k in data, f"Key '{k}' not found in JSON"
            data = data[k]
        if value is not None:
            assert data == value, f"Key '{key}': expected '{value}', got '{data}'"
        return self


@dataclass
class _ASGIReceive:
    """ASGI receive callable for test client."""

    body: bytes = b""
    _sent: bool = False

    async def __call__(self) -> dict[str, Any]:
        """Return request body message."""
        if not self._sent:
            self._sent = True
            return {
                "type": "http.request",
                "body": self.body,
                "more_body": False,
            }
        # After body is sent, return disconnect
        return {"type": "http.disconnect"}


@dataclass
class _ASGISend:
    """ASGI send callable for test client."""

    status_code: int = 200
    headers: list[tuple[bytes, bytes]] = field(default_factory=list)
    body_parts: list[bytes] = field(default_factory=list)
    _started: bool = False
    _finished: bool = False

    async def __call__(self, message: Message) -> None:
        """Handle ASGI send message."""
        if message["type"] == "http.response.start":
            self.status_code = message["status"]
            self.headers = list(message.get("headers", []))
            self._started = True
        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            if body:
                self.body_parts.append(body)
            if not message.get("more_body", False):
                self._finished = True

    def get_response(self) -> TestResponse:
        """Convert captured data to TestResponse."""
        headers: dict[str, str] = {}
        raw_headers: list[tuple[str, str]] = []
        for key, value in self.headers:
            header_name = key.decode("latin-1").lower()
            header_value = value.decode("latin-1")
            raw_headers.append((header_name, header_value))
            # RFC 7230: combine multiple header values with comma
            # Exception: Set-Cookie headers should not be combined
            if header_name != "set-cookie":
                if header_name in headers:
                    headers[header_name] = f"{headers[header_name]}, {header_value}"
                else:
                    headers[header_name] = header_value
            # Set-Cookie is available via raw_headers or cookies property

        return TestResponse(
            status_code=self.status_code,
            headers=headers,
            body=b"".join(self.body_parts),
            raw_headers=raw_headers,
        )


class TestClient:
    __test__ = False  # Prevent pytest from collecting this class

    """Test client for ASGI applications.

    Provides a simple interface for testing Pykour applications
    without running an HTTP server.

    Example:
        from pykour import Pykour
        from pykour.testing import TestClient

        app = Pykour(routes_dir="routes")
        client = TestClient(app)

        # Simple GET request
        response = await client.get("/users")
        assert response.status_code == 200

        # POST with JSON body
        response = await client.post("/users", json={"name": "Alice"})
        assert response.status_code == 201

        # With query parameters
        response = await client.get("/search", params={"q": "test"})

        # With custom headers
        response = await client.get(
            "/protected",
            headers={"Authorization": "Bearer token123"}
        )

        # With cookies
        client = TestClient(app, cookies={"session": "abc123"})
        response = await client.get("/dashboard")

        # Conditional requests (ETag)
        response1 = await client.get("/resource")
        response2 = await client.get("/resource", if_none_match=response1.etag)
        assert response2.status_code == 304

        # WebSocket
        async with client.websocket_connect("/ws") as ws:
            await ws.send_text("hello")
            msg = await ws.receive_text()
    """

    def __init__(
        self,
        app: ASGIApp,
        base_url: str = "http://testserver",
        default_headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> None:
        """Initialize test client.

        Args:
            app: The ASGI application to test.
            base_url: Base URL for requests (used in headers).
            default_headers: Headers to include in every request.
            cookies: Initial cookies to include in requests.
        """
        self.app = app
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}
        self.cookie_jar = CookieJar()

        # Set initial cookies
        if cookies:
            for name, value in cookies.items():
                self.cookie_jar.set(name, value)

    def _build_scope(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build ASGI scope for a request.

        Args:
            method: HTTP method.
            path: Request path.
            headers: Request headers.
            query_params: Query parameters.

        Returns:
            ASGI scope dictionary.
        """
        # Build query string
        query_string = b""
        if query_params:
            query_string = urlencode(query_params, doseq=True).encode("utf-8")

        # Build headers
        all_headers = {**self.default_headers}
        if headers:
            all_headers.update(headers)

        # Add host header if not present
        if "host" not in {k.lower() for k in all_headers}:
            all_headers["host"] = "testserver"

        header_list = [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in all_headers.items()
        ]

        return {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method.upper(),
            "path": path,
            "root_path": "",
            "query_string": query_string,
            "headers": header_list,
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: bytes | str | None = None,
        content_type: str | None = None,
        cookies: dict[str, str] | None = None,
        if_none_match: str | None = None,
        if_modified_since: str | None = None,
    ) -> TestResponse:
        """Send an HTTP request to the application.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.).
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            json: JSON body (will be serialized).
            data: Raw body data.
            content_type: Content-Type header.
            cookies: Cookies to include in this request (also added to jar).
            if_none_match: ETag value for conditional request (If-None-Match).
            if_modified_since: Date string for conditional request (If-Modified-Since).

        Returns:
            TestResponse object.
        """
        request_headers = dict(headers) if headers else {}

        # Add request-specific cookies to the jar
        if cookies:
            for name, value in cookies.items():
                self.cookie_jar.set(name, value)

        # Add Cookie header from jar
        cookie_header = self.cookie_jar.get_cookie_header(path)
        if cookie_header:
            request_headers["cookie"] = cookie_header

        # Add conditional request headers
        if if_none_match:
            request_headers["if-none-match"] = if_none_match
        if if_modified_since:
            request_headers["if-modified-since"] = if_modified_since

        # Handle body
        body = b""
        if json is not None:
            import json as json_module

            body = json_module.dumps(json).encode("utf-8")
            if "content-type" not in {k.lower() for k in request_headers}:
                request_headers["content-type"] = "application/json"
        elif data is not None:
            if isinstance(data, str):
                body = data.encode("utf-8")
            else:
                body = data

        if content_type:
            request_headers["content-type"] = content_type

        if body and "content-length" not in {k.lower() for k in request_headers}:
            request_headers["content-length"] = str(len(body))

        scope = self._build_scope(method, path, request_headers, params)
        receive = _ASGIReceive(body=body)
        send = _ASGISend()

        await self.app(scope, receive, send)

        response = send.get_response()

        # Update cookie jar from Set-Cookie headers
        self.cookie_jar.update_from_response(response.raw_headers)

        return response

    async def get(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        cookies: dict[str, str] | None = None,
        if_none_match: str | None = None,
        if_modified_since: str | None = None,
    ) -> TestResponse:
        """Send a GET request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            cookies: Cookies to include in this request.
            if_none_match: ETag value for conditional request.
            if_modified_since: Date string for conditional request.

        Returns:
            TestResponse object.
        """
        return await self.request(
            "GET",
            path,
            headers=headers,
            params=params,
            cookies=cookies,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
        )

    async def post(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: bytes | str | None = None,
        content_type: str | None = None,
        cookies: dict[str, str] | None = None,
        if_none_match: str | None = None,
        if_modified_since: str | None = None,
    ) -> TestResponse:
        """Send a POST request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            json: JSON body.
            data: Raw body data.
            content_type: Content-Type header.
            cookies: Cookies to include in this request.
            if_none_match: ETag value for conditional request.
            if_modified_since: Date string for conditional request.

        Returns:
            TestResponse object.
        """
        return await self.request(
            "POST",
            path,
            headers=headers,
            params=params,
            json=json,
            data=data,
            content_type=content_type,
            cookies=cookies,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
        )

    async def put(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: bytes | str | None = None,
        content_type: str | None = None,
        cookies: dict[str, str] | None = None,
        if_none_match: str | None = None,
        if_modified_since: str | None = None,
    ) -> TestResponse:
        """Send a PUT request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            json: JSON body.
            data: Raw body data.
            content_type: Content-Type header.
            cookies: Cookies to include in this request.
            if_none_match: ETag value for conditional request.
            if_modified_since: Date string for conditional request.

        Returns:
            TestResponse object.
        """
        return await self.request(
            "PUT",
            path,
            headers=headers,
            params=params,
            json=json,
            data=data,
            content_type=content_type,
            cookies=cookies,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
        )

    async def patch(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: bytes | str | None = None,
        content_type: str | None = None,
        cookies: dict[str, str] | None = None,
        if_none_match: str | None = None,
        if_modified_since: str | None = None,
    ) -> TestResponse:
        """Send a PATCH request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            json: JSON body.
            data: Raw body data.
            content_type: Content-Type header.
            cookies: Cookies to include in this request.
            if_none_match: ETag value for conditional request.
            if_modified_since: Date string for conditional request.

        Returns:
            TestResponse object.
        """
        return await self.request(
            "PATCH",
            path,
            headers=headers,
            params=params,
            json=json,
            data=data,
            content_type=content_type,
            cookies=cookies,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
        )

    async def delete(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: bytes | str | None = None,
        content_type: str | None = None,
        cookies: dict[str, str] | None = None,
        if_none_match: str | None = None,
        if_modified_since: str | None = None,
    ) -> TestResponse:
        """Send a DELETE request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            json: JSON body (some APIs accept body in DELETE requests).
            data: Raw body data.
            content_type: Content-Type header.
            cookies: Cookies to include in this request.
            if_none_match: ETag value for conditional request.
            if_modified_since: Date string for conditional request.

        Returns:
            TestResponse object.
        """
        return await self.request(
            "DELETE",
            path,
            headers=headers,
            params=params,
            json=json,
            data=data,
            content_type=content_type,
            cookies=cookies,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
        )

    async def post_multipart(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        form_data: dict[str, str] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> TestResponse:
        """Send a POST request with multipart/form-data.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            form_data: Form fields {field_name: value}.
            files: Files to upload {field_name: (filename, content, content_type)}.
            cookies: Cookies to include in this request.

        Returns:
            TestResponse object.

        Example:
            response = await client.post_multipart(
                "/upload",
                form_data={"description": "Test file"},
                files={"avatar": ("test.png", b"...", "image/png")},
            )
        """
        boundary = "----PykourTestBoundary"
        body_parts: list[bytes] = []

        # Add form fields
        if form_data:
            for name, value in form_data.items():
                body_parts.append(f"--{boundary}\r\n".encode())
                body_parts.append(
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
                )
                body_parts.append(f"{value}\r\n".encode())

        # Add files
        if files:
            for name, (filename, content, content_type) in files.items():
                body_parts.append(f"--{boundary}\r\n".encode())
                body_parts.append(
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'.encode()
                )
                body_parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
                body_parts.append(content)
                body_parts.append(b"\r\n")

        body_parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(body_parts)

        request_headers = dict(headers) if headers else {}
        request_headers["content-type"] = f"multipart/form-data; boundary={boundary}"

        return await self.request(
            "POST",
            path,
            headers=request_headers,
            params=params,
            data=body,
            cookies=cookies,
        )

    async def head(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        cookies: dict[str, str] | None = None,
        if_none_match: str | None = None,
        if_modified_since: str | None = None,
    ) -> TestResponse:
        """Send a HEAD request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            cookies: Cookies to include in this request.
            if_none_match: ETag value for conditional request.
            if_modified_since: Date string for conditional request.

        Returns:
            TestResponse object.
        """
        return await self.request(
            "HEAD",
            path,
            headers=headers,
            params=params,
            cookies=cookies,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
        )

    async def options(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        cookies: dict[str, str] | None = None,
        if_none_match: str | None = None,
        if_modified_since: str | None = None,
    ) -> TestResponse:
        """Send an OPTIONS request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            cookies: Cookies to include in this request.
            if_none_match: ETag value for conditional request.
            if_modified_since: Date string for conditional request.

        Returns:
            TestResponse object.
        """
        return await self.request(
            "OPTIONS",
            path,
            headers=headers,
            params=params,
            cookies=cookies,
            if_none_match=if_none_match,
            if_modified_since=if_modified_since,
        )

    def websocket_connect(
        self,
        path: str,
        headers: dict[str, str] | None = None,
        subprotocols: list[str] | None = None,
    ) -> "WebSocketTestSession":
        """Create a WebSocket test session.

        Args:
            path: WebSocket path.
            headers: Optional connection headers.
            subprotocols: Optional list of subprotocols.

        Returns:
            WebSocketTestSession for interacting with the WebSocket.

        Example:
            async with client.websocket_connect("/ws/chat") as ws:
                await ws.send_text("Hello")
                message = await ws.receive_text()
                assert message == "Echo: Hello"
        """
        from pykour.testing.websocket import WebSocketTestSession

        all_headers = {**self.default_headers}
        if headers:
            all_headers.update(headers)

        return WebSocketTestSession(
            self.app,
            path,
            headers=all_headers,
            subprotocols=subprotocols,
        )


class SyncTestClient:
    """Synchronous wrapper for TestClient.

    Useful for tests that don't use pytest-asyncio.

    Example:
        client = SyncTestClient(app)
        response = client.get("/users")
        assert response.status_code == 200

        # With cookies
        client = SyncTestClient(app, cookies={"session": "abc123"})
        response = client.get("/dashboard")
    """

    def __init__(
        self,
        app: ASGIApp,
        base_url: str = "http://testserver",
        default_headers: dict[str, str] | None = None,
        cookies: dict[str, str] | None = None,
    ) -> None:
        """Initialize sync test client.

        Args:
            app: The ASGI application to test.
            base_url: Base URL for requests.
            default_headers: Headers to include in every request.
            cookies: Initial cookies to include in requests.
        """
        self._client = TestClient(app, base_url, default_headers, cookies)

    @property
    def cookie_jar(self) -> CookieJar:
        """Access the cookie jar for manual cookie management."""
        return self._client.cookie_jar

    def _run(self, coro: Any) -> Any:
        """Run a coroutine synchronously."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> TestResponse:
        """Send an HTTP request."""
        return self._run(self._client.request(method, path, **kwargs))

    def get(self, path: str, **kwargs: Any) -> TestResponse:
        """Send a GET request."""
        return self._run(self._client.get(path, **kwargs))

    def post(self, path: str, **kwargs: Any) -> TestResponse:
        """Send a POST request."""
        return self._run(self._client.post(path, **kwargs))

    def put(self, path: str, **kwargs: Any) -> TestResponse:
        """Send a PUT request."""
        return self._run(self._client.put(path, **kwargs))

    def patch(self, path: str, **kwargs: Any) -> TestResponse:
        """Send a PATCH request."""
        return self._run(self._client.patch(path, **kwargs))

    def delete(self, path: str, **kwargs: Any) -> TestResponse:
        """Send a DELETE request."""
        return self._run(self._client.delete(path, **kwargs))

    def post_multipart(self, path: str, **kwargs: Any) -> TestResponse:
        """Send a POST request with multipart/form-data."""
        return self._run(self._client.post_multipart(path, **kwargs))

    def head(self, path: str, **kwargs: Any) -> TestResponse:
        """Send a HEAD request."""
        return self._run(self._client.head(path, **kwargs))

    def options(self, path: str, **kwargs: Any) -> TestResponse:
        """Send an OPTIONS request."""
        return self._run(self._client.options(path, **kwargs))
