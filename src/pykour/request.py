"""HTTP Request wrapper for ASGI scope."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pykour import json as pykour_json
from pykour.schema.parser import parse_query_string
from pykour.types import Receive, Scope

if TYPE_CHECKING:
    from pykour.datastructures import FormData


class State:
    """Mutable state object for storing request-scoped data.

    This class allows middleware to share data with route handlers.
    Data can be set and accessed as attributes.

    Example:
        request.state.user = {"id": 123, "name": "John"}
        user = request.state.user
    """

    def __setattr__(self, name: str, value: Any) -> None:
        self.__dict__[name] = value

    def __getattr__(self, name: str) -> Any:
        try:
            return self.__dict__[name]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

    def __delattr__(self, name: str) -> None:
        try:
            del self.__dict__[name]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )


class Request:
    """Represents an HTTP request."""

    def __init__(
        self,
        scope: Scope,
        receive: Receive,
        path_params: dict[str, str] | None = None,
    ) -> None:
        self._scope = scope
        self._receive = receive
        self._body: bytes | None = None
        self._json: dict[str, Any] | None = None
        self._query_params: dict[str, str | list[str]] | None = None
        self._path_params = path_params or {}
        self._state: State | None = None
        self._cookies: dict[str, str] | None = None
        self._form_data: FormData | None = None

    @property
    def path_params(self) -> dict[str, str]:
        """Path parameters extracted from dynamic route segments."""
        return self._path_params

    @property
    def method(self) -> str:
        """HTTP method (GET, POST, etc.)."""
        return self._scope.get("method", "GET")

    @property
    def path(self) -> str:
        """Request path."""
        return self._scope.get("path", "/")

    @property
    def query_string(self) -> bytes:
        """Raw query string."""
        return self._scope.get("query_string", b"")

    @property
    def headers(self) -> dict[str, str]:
        """Request headers as a dictionary."""
        raw_headers: list[tuple[bytes, bytes]] = self._scope.get("headers", [])
        return {
            key.decode("latin-1"): value.decode("latin-1") for key, value in raw_headers
        }

    @property
    def scheme(self) -> str:
        """URL scheme (http or https)."""
        return self._scope.get("scheme", "http")

    @property
    def server(self) -> tuple[str, int] | None:
        """Server host and port."""
        return self._scope.get("server")

    @property
    def http_version(self) -> str:
        """HTTP version."""
        return self._scope.get("http_version", "1.1")

    @property
    def scope(self) -> Scope:
        """Raw ASGI scope."""
        return self._scope

    @property
    def receive(self) -> Receive:
        """ASGI receive callable for streaming body."""
        return self._receive

    @property
    def state(self) -> State:
        """Request state for storing middleware data.

        This property provides access to a mutable state object that
        middleware can use to share data with route handlers.

        If a middleware has set 'user' in the ASGI scope, it will be
        automatically available as request.state.user.
        """
        if self._state is None:
            self._state = State()
            # Load user from scope if set by auth middleware
            if "user" in self._scope:
                self._state.user = self._scope["user"]
        return self._state

    @property
    def user(self) -> Any:
        """Convenience property to access authenticated user.

        This is a shortcut for request.state.user, commonly used
        in route handlers after authentication middleware.

        Returns:
            The user object set by authentication middleware, or None
            if no user is authenticated.

        Example:
            async def handler(request: Request) -> JSONResponse:
                if request.user:
                    return JSONResponse({"message": f"Hello, {request.user['name']}"})
                return JSONResponse({"error": "Not authenticated"}, status_code=401)
        """
        return getattr(self.state, "user", None)

    @property
    def cookies(self) -> dict[str, str]:
        """Parsed cookies from Cookie header.

        Returns:
            Dictionary mapping cookie names to values.

        Example:
            session_id = request.cookies.get("session_id")
        """
        if self._cookies is None:
            self._cookies = self._parse_cookies()
        return self._cookies

    def get_cookie(self, name: str, default: str | None = None) -> str | None:
        """Get a cookie value by name.

        Args:
            name: Cookie name.
            default: Default value if cookie not found.

        Returns:
            Cookie value or default.

        Example:
            token = request.get_cookie("csrf_token")
        """
        return self.cookies.get(name, default)

    def _parse_cookies(self) -> dict[str, str]:
        """Parse Cookie header into dict."""
        cookie_header = self.headers.get("cookie", "")
        cookies: dict[str, str] = {}
        if cookie_header:
            for item in cookie_header.split(";"):
                item = item.strip()
                if "=" in item:
                    name, _, value = item.partition("=")
                    cookies[name.strip()] = value.strip()
        return cookies

    async def body(self) -> bytes:
        """Read and return the request body."""
        if self._body is not None:
            return self._body

        chunks: list[bytes] = []
        while True:
            message = await self._receive()
            body = message.get("body", b"")
            if body:
                chunks.append(body)
            if not message.get("more_body", False):
                break

        self._body = b"".join(chunks)
        return self._body

    @property
    def query_params(self) -> dict[str, str | list[str]]:
        """Parsed query parameters."""
        if self._query_params is None:
            self._query_params = self._parse_query_string()
        return self._query_params

    def _parse_query_string(self) -> dict[str, str | list[str]]:
        """Parse query string to dict."""
        return parse_query_string(self.query_string)

    async def json(self) -> dict[str, Any]:
        """Parse body as JSON."""
        if self._json is None:
            body = await self.body()
            if not body:
                self._json = {}
            else:
                self._json = pykour_json.loads(body)
        return self._json

    async def form(self) -> FormData:
        """Parse and return form data from request body.

        Supports both application/x-www-form-urlencoded and
        multipart/form-data content types.

        Returns:
            FormData object containing fields and files.

        Raises:
            ValidationError: If Content-Type is invalid or parsing fails.

        Example:
            form_data = await request.form()
            name = form_data.fields.get("name")
            avatar = form_data.files.get("avatar")
        """
        if self._form_data is not None:
            return self._form_data

        from pykour.datastructures import FormData
        from pykour.injection.form_parsers import parse_multipart, parse_urlencoded

        content_type = self.headers.get("content-type", "")

        if "multipart/form-data" in content_type:
            self._form_data = await parse_multipart(self)
        elif "application/x-www-form-urlencoded" in content_type:
            self._form_data = await parse_urlencoded(self)
        else:
            # Return empty FormData for unsupported content types
            self._form_data = FormData(fields={}, files={})

        return self._form_data
