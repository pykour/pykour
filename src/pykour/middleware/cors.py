"""CORS middleware for Pykour."""

from __future__ import annotations

import re
from typing import Any, Pattern, Sequence

from pykour.middleware.base import BaseMiddleware, Receive, Scope, Send
from pykour.middleware.utils import extract_header, extract_headers_dict
from pykour.response import Response


class CORSMiddleware(BaseMiddleware):
    """CORS (Cross-Origin Resource Sharing) middleware.

    Handles CORS preflight requests and adds appropriate CORS headers
    to responses.

    Example:
        # Allow all origins
        app.add_middleware(CORSMiddleware, allow_origins=["*"])

        # Allow specific origins
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://example.com"],
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
            allow_credentials=True,
            max_age=3600,
        )

        # Allow origins with wildcard pattern
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://*.example.com"],
        )
    """

    def __init__(
        self,
        app: Any,
        *,
        allow_origins: Sequence[str] = (),
        allow_methods: Sequence[str] = ("GET",),
        allow_headers: Sequence[str] = (),
        allow_credentials: bool = False,
        expose_headers: Sequence[str] = (),
        max_age: int = 600,
    ) -> None:
        """Initialize CORS middleware.

        Args:
            app: The ASGI application to wrap.
            allow_origins: List of allowed origins. Use "*" to allow all origins.
                           Supports wildcard patterns like "https://*.example.com".
            allow_methods: List of allowed HTTP methods.
            allow_headers: List of allowed request headers.
            allow_credentials: Whether to allow credentials (cookies, auth headers).
            expose_headers: List of headers exposed to the browser.
            max_age: Maximum time (seconds) for browser to cache preflight response.
        """
        super().__init__(app)
        self.allow_origins = list(allow_origins)
        self.allow_methods = list(allow_methods)
        self.allow_headers = [h.lower() for h in allow_headers]
        self.allow_credentials = allow_credentials
        self.expose_headers = list(expose_headers)
        self.max_age = max_age

        # Pre-compute settings
        self._allow_all_origins = "*" in self.allow_origins
        self._origin_patterns: list[Pattern[str]] = self._compile_origin_patterns()
        self._simple_origins: set[str] = {o for o in self.allow_origins if "*" not in o}

    def _compile_origin_patterns(self) -> list[Pattern[str]]:
        """Compile wildcard origins into regex patterns."""
        patterns: list[Pattern[str]] = []
        for origin in self.allow_origins:
            if origin == "*":
                continue
            if "*" in origin:
                # Convert wildcard pattern to regex
                # https://*.example.com -> ^https://[^/]+\.example\.com$
                pattern = re.escape(origin).replace(r"\*", r"[^/]+")
                patterns.append(re.compile(f"^{pattern}$"))
        return patterns

    def _get_origin(self, scope: Scope) -> str | None:
        """Extract Origin header from request."""
        return extract_header(scope, b"origin")

    def _get_request_headers(self, scope: Scope) -> dict[str, str]:
        """Extract headers from scope as dict."""
        return extract_headers_dict(scope, lowercase_keys=True)

    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if the origin is allowed."""
        if self._allow_all_origins:
            return True
        if origin in self._simple_origins:
            return True
        for pattern in self._origin_patterns:
            if pattern.match(origin):
                return True
        return False

    def _is_preflight_request(self, scope: Scope, headers: dict[str, str]) -> bool:
        """Check if request is a CORS preflight request."""
        return (
            scope.get("method") == "OPTIONS"
            and "access-control-request-method" in headers
        )

    def _preflight_response(
        self,
        origin: str | None,
        request_headers: dict[str, str],
    ) -> Response:
        """Generate preflight response.

        Returns 200 with CORS headers if origin is allowed,
        403 Forbidden if origin is not allowed.
        """
        # If no origin header, deny the request
        if not origin:
            return Response(
                content=b"CORS origin header required",
                status_code=403,
                headers={"Vary": "Origin"},
            )

        # If origin is not allowed, return 403
        if not self._is_origin_allowed(origin):
            return Response(
                content=b"CORS origin not allowed",
                status_code=403,
                headers={"Vary": "Origin"},
            )

        # Origin is allowed - build success response
        headers: dict[str, str] = {"Vary": "Origin"}

        # Set allowed origin
        if self._allow_all_origins and not self.allow_credentials:
            headers["Access-Control-Allow-Origin"] = "*"
        else:
            headers["Access-Control-Allow-Origin"] = origin

        # Set allowed methods
        headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)

        # Set max age
        headers["Access-Control-Max-Age"] = str(self.max_age)

        # Set allowed headers
        if self.allow_headers:
            headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        else:
            # Echo back the requested headers
            requested_headers = request_headers.get(
                "access-control-request-headers", ""
            )
            if requested_headers:
                headers["Access-Control-Allow-Headers"] = requested_headers

        # Set credentials
        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"

        return Response(content=b"", status_code=200, headers=headers)

    async def _handle_request_with_cors(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        origin: str | None,
    ) -> None:
        """Handle request and add CORS headers to response."""

        async def send_with_cors(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))

                if origin and self._is_origin_allowed(origin):
                    # Add Access-Control-Allow-Origin
                    if self._allow_all_origins and not self.allow_credentials:
                        headers.append((b"access-control-allow-origin", b"*"))
                    else:
                        headers.append(
                            (b"access-control-allow-origin", origin.encode("latin-1"))
                        )

                    # Add credentials header
                    if self.allow_credentials:
                        headers.append((b"access-control-allow-credentials", b"true"))

                    # Add expose headers
                    if self.expose_headers:
                        headers.append(
                            (
                                b"access-control-expose-headers",
                                ", ".join(self.expose_headers).encode("latin-1"),
                            )
                        )

                # Always add Vary: Origin to prevent cache poisoning
                # This must be present regardless of origin presence or allowance
                headers.append((b"vary", b"Origin"))

                message = {**message, "headers": headers}

            await send(message)

        await self.app(scope, receive, send_with_cors)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        origin = self._get_origin(scope)
        headers = self._get_request_headers(scope)

        # Handle preflight request
        if self._is_preflight_request(scope, headers):
            response = self._preflight_response(origin, headers)
            await response(scope, receive, send)
            return

        # Handle simple/actual request
        await self._handle_request_with_cors(scope, receive, send, origin)
