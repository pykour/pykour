"""Test client for Pykour applications."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from pykour.types import Message

if TYPE_CHECKING:
    from pykour.types import ASGIApp


@dataclass
class TestResponse:
    __test__ = False  # Prevent pytest from collecting this class
    """Response object returned by TestClient.

    Attributes:
        status_code: HTTP status code.
        headers: Response headers as a dictionary.
        body: Raw response body bytes.
    """

    status_code: int
    headers: dict[str, str]
    body: bytes

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
        headers = {}
        for key, value in self.headers:
            header_name = key.decode("latin-1").lower()
            header_value = value.decode("latin-1")
            headers[header_name] = header_value

        return TestResponse(
            status_code=self.status_code,
            headers=headers,
            body=b"".join(self.body_parts),
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
    """

    def __init__(
        self,
        app: ASGIApp,
        base_url: str = "http://testserver",
        default_headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize test client.

        Args:
            app: The ASGI application to test.
            base_url: Base URL for requests (used in headers).
            default_headers: Headers to include in every request.
        """
        self.app = app
        self.base_url = base_url.rstrip("/")
        self.default_headers = default_headers or {}

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

        Returns:
            TestResponse object.
        """
        request_headers = dict(headers) if headers else {}

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

        return send.get_response()

    async def get(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> TestResponse:
        """Send a GET request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.

        Returns:
            TestResponse object.
        """
        return await self.request("GET", path, headers=headers, params=params)

    async def post(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        data: bytes | str | None = None,
        content_type: str | None = None,
    ) -> TestResponse:
        """Send a POST request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            json: JSON body.
            data: Raw body data.
            content_type: Content-Type header.

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
    ) -> TestResponse:
        """Send a PUT request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            json: JSON body.
            data: Raw body data.
            content_type: Content-Type header.

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
    ) -> TestResponse:
        """Send a PATCH request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            json: JSON body.
            data: Raw body data.
            content_type: Content-Type header.

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
    ) -> TestResponse:
        """Send a DELETE request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.
            json: JSON body (some APIs accept body in DELETE requests).
            data: Raw body data.
            content_type: Content-Type header.

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
        )

    async def head(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> TestResponse:
        """Send a HEAD request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.

        Returns:
            TestResponse object.
        """
        return await self.request("HEAD", path, headers=headers, params=params)

    async def options(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
    ) -> TestResponse:
        """Send an OPTIONS request.

        Args:
            path: Request path.
            headers: Request headers.
            params: Query parameters.

        Returns:
            TestResponse object.
        """
        return await self.request("OPTIONS", path, headers=headers, params=params)


class SyncTestClient:
    """Synchronous wrapper for TestClient.

    Useful for tests that don't use pytest-asyncio.

    Example:
        client = SyncTestClient(app)
        response = client.get("/users")
        assert response.status_code == 200
    """

    def __init__(
        self,
        app: ASGIApp,
        base_url: str = "http://testserver",
        default_headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize sync test client.

        Args:
            app: The ASGI application to test.
            base_url: Base URL for requests.
            default_headers: Headers to include in every request.
        """
        self._client = TestClient(app, base_url, default_headers)

    def _run(self, coro: Any) -> Any:
        """Run a coroutine synchronously."""
        return asyncio.get_event_loop().run_until_complete(coro)

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

    def head(self, path: str, **kwargs: Any) -> TestResponse:
        """Send a HEAD request."""
        return self._run(self._client.head(path, **kwargs))

    def options(self, path: str, **kwargs: Any) -> TestResponse:
        """Send an OPTIONS request."""
        return self._run(self._client.options(path, **kwargs))
