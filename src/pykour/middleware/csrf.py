"""CSRF protection middleware for Pykour."""

from __future__ import annotations

import hmac
import secrets
from typing import Any, Sequence

from pykour.middleware.base import BaseMiddleware
from pykour.middleware.utils import extract_header
from pykour.response import JSONResponse
from pykour.types import Receive, Scope, Send

# Safe HTTP methods that don't require CSRF validation
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

# Default token length in bytes (32 bytes = 256 bits)
DEFAULT_TOKEN_BYTES = 32


class CSRFMiddleware(BaseMiddleware):
    """CSRF protection middleware using Double Submit Cookie pattern.

    This middleware protects against Cross-Site Request Forgery attacks by:
    1. Setting a CSRF token in a cookie
    2. Requiring the same token in a header for unsafe methods
    3. Using timing-safe comparison to verify tokens

    Example:
        # Basic usage
        app.add_middleware(CSRFMiddleware)

        # Custom configuration
        app.add_middleware(
            CSRFMiddleware,
            cookie_name="csrf_token",
            header_name="X-CSRF-Token",
            cookie_secure=True,
            exclude_paths=["/api/webhook"],
        )

    Client-side usage:
        1. Read the CSRF token from the cookie
        2. Include it in the X-CSRF-Token header for POST/PUT/PATCH/DELETE requests
    """

    def __init__(
        self,
        app: Any,
        *,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        cookie_path: str = "/",
        cookie_domain: str | None = None,
        cookie_secure: bool = False,
        cookie_httponly: bool = False,  # False so JS can read it
        cookie_samesite: str = "Lax",
        cookie_max_age: int = 86400,  # 24 hours
        token_bytes: int = DEFAULT_TOKEN_BYTES,
        exclude_paths: Sequence[str] = (),
        exclude_methods: Sequence[str] = (),
    ) -> None:
        """Initialize CSRF middleware.

        Args:
            app: The ASGI application to wrap.
            cookie_name: Name of the CSRF cookie.
            header_name: Name of the CSRF header.
            cookie_path: Cookie path.
            cookie_domain: Cookie domain.
            cookie_secure: Require HTTPS for cookie.
            cookie_httponly: HttpOnly flag (should be False for JS access).
            cookie_samesite: SameSite cookie policy.
            cookie_max_age: Cookie max age in seconds.
            token_bytes: Token length in bytes.
            exclude_paths: Paths to exclude from CSRF protection.
            exclude_methods: Additional methods to exclude (beyond safe methods).
        """
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.cookie_path = cookie_path
        self.cookie_domain = cookie_domain
        self.cookie_secure = cookie_secure
        self.cookie_httponly = cookie_httponly
        self.cookie_samesite = cookie_samesite
        self.cookie_max_age = cookie_max_age
        self.token_bytes = token_bytes
        self.exclude_paths = list(exclude_paths)
        self.safe_methods = SAFE_METHODS | frozenset(m.upper() for m in exclude_methods)

        # Pre-compute header name as bytes for extraction
        self._header_name_bytes = header_name.lower().encode("latin-1")

    def _generate_token(self) -> str:
        """Generate a cryptographically secure CSRF token."""
        return secrets.token_hex(self.token_bytes)

    def _get_cookie_token(self, scope: Scope) -> str | None:
        """Extract CSRF token from cookie header."""
        cookie_header = extract_header(scope, b"cookie")
        if not cookie_header:
            return None

        for item in cookie_header.split(";"):
            item = item.strip()
            if "=" in item:
                name, _, value = item.partition("=")
                if name.strip() == self.cookie_name:
                    return value.strip()
        return None

    def _get_header_token(self, scope: Scope) -> str | None:
        """Extract CSRF token from request header."""
        return extract_header(scope, self._header_name_bytes)

    def _verify_tokens(self, cookie_token: str, header_token: str) -> bool:
        """Verify CSRF tokens using timing-safe comparison."""
        if not cookie_token or not header_token:
            return False
        return hmac.compare_digest(cookie_token, header_token)

    def _build_cookie_header(self, token: str) -> tuple[bytes, bytes]:
        """Build Set-Cookie header for CSRF token."""
        parts = [f"{self.cookie_name}={token}"]

        if self.cookie_max_age is not None:
            parts.append(f"Max-Age={self.cookie_max_age}")
        if self.cookie_path:
            parts.append(f"Path={self.cookie_path}")
        if self.cookie_domain:
            parts.append(f"Domain={self.cookie_domain}")
        if self.cookie_secure:
            parts.append("Secure")
        if self.cookie_httponly:
            parts.append("HttpOnly")
        if self.cookie_samesite:
            parts.append(f"SameSite={self.cookie_samesite}")

        cookie_value = "; ".join(parts)
        return (b"set-cookie", cookie_value.encode("latin-1"))

    def _forbidden_response(self, detail: str) -> JSONResponse:
        """Create 403 Forbidden response for CSRF failures."""
        return JSONResponse(
            {"error": "Forbidden", "detail": detail},
            status_code=403,
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request with CSRF protection."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")
        method = scope.get("method", "GET").upper()

        # Skip CSRF for excluded paths
        if not self.should_process_path(path, self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # Get existing token from cookie
        cookie_token = self._get_cookie_token(scope)

        # For safe methods, just ensure token exists and add to response if missing
        if method in self.safe_methods:
            if cookie_token:
                # Token exists, pass through
                await self.app(scope, receive, send)
            else:
                # Generate new token and add to response
                new_token = self._generate_token()
                await self._send_with_csrf_cookie(scope, receive, send, new_token)
            return

        # For unsafe methods, validate CSRF token
        if not cookie_token:
            response = self._forbidden_response("CSRF cookie missing")
            await response(scope, receive, send)
            return

        header_token = self._get_header_token(scope)
        if not header_token:
            response = self._forbidden_response("CSRF header missing")
            await response(scope, receive, send)
            return

        if not self._verify_tokens(cookie_token, header_token):
            response = self._forbidden_response("CSRF token mismatch")
            await response(scope, receive, send)
            return

        # Token valid, continue with request
        await self.app(scope, receive, send)

    async def _send_with_csrf_cookie(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        token: str,
    ) -> None:
        """Wrap send to add CSRF cookie to response."""
        csrf_cookie = self._build_cookie_header(token)

        async def send_with_cookie(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append(csrf_cookie)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_cookie)
