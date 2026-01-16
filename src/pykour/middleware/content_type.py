"""Content-Type validation middleware for Pykour."""

from __future__ import annotations

from typing import Any, Sequence

from pykour.middleware.base import BaseMiddleware
from pykour.middleware.utils import extract_header, is_path_excluded
from pykour.response import JSONResponse
from pykour.types import Receive, Scope, Send


class ContentTypeMiddleware(BaseMiddleware):
    """Middleware that validates Content-Type header.

    Validates that incoming requests have an acceptable Content-Type header.
    Returns 415 Unsupported Media Type for invalid content types.

    Example:
        # Only allow JSON
        app.add_middleware(
            ContentTypeMiddleware,
            allowed_types=["application/json"],
        )

        # Allow JSON and form data
        app.add_middleware(
            ContentTypeMiddleware,
            allowed_types=[
                "application/json",
                "application/x-www-form-urlencoded",
                "multipart/form-data",
            ],
        )

        # Use wildcard patterns
        app.add_middleware(
            ContentTypeMiddleware,
            allowed_types=["application/*", "text/*"],
        )
    """

    def __init__(
        self,
        app: Any,
        *,
        allowed_types: Sequence[str] = ("application/json",),
        require_content_type: bool = True,
        safe_methods: Sequence[str] = ("GET", "HEAD", "OPTIONS", "TRACE"),
        exclude_paths: Sequence[str] = (),
    ) -> None:
        """Initialize Content-Type validation middleware.

        Args:
            app: The ASGI application to wrap.
            allowed_types: List of allowed Content-Type values.
                Supports wildcards like "application/*" or "*/*".
            require_content_type: If True, requests with body but no
                Content-Type header will be rejected.
            safe_methods: HTTP methods to skip validation (no body expected).
            exclude_paths: Paths to exclude from validation.
        """
        super().__init__(app)
        self.allowed_types = list(allowed_types)
        self.require_content_type = require_content_type
        self.safe_methods = set(method.upper() for method in safe_methods)
        self.exclude_paths = list(exclude_paths)

    def _match_content_type(self, content_type: str, pattern: str) -> bool:
        """Check if content type matches pattern.

        Supports wildcards:
        - "*/*" matches everything
        - "application/*" matches any application type
        - "application/json" matches exactly
        """
        # Normalize to lowercase
        content_type = content_type.lower()
        pattern = pattern.lower()

        # Handle wildcard */*
        if pattern == "*/*":
            return True

        # Split type/subtype
        if "/" not in content_type or "/" not in pattern:
            return content_type == pattern

        ct_type, ct_subtype = content_type.split("/", 1)
        pat_type, pat_subtype = pattern.split("/", 1)

        # Check type match
        if pat_type != "*" and ct_type != pat_type:
            return False

        # Check subtype match
        if pat_subtype != "*" and ct_subtype != pat_subtype:
            return False

        return True

    def _is_allowed(self, content_type: str) -> bool:
        """Check if content type is in allowed list."""
        # Extract base type (without parameters like charset)
        base_type = content_type.split(";")[0].strip()

        for pattern in self.allowed_types:
            if self._match_content_type(base_type, pattern):
                return True
        return False

    def _unsupported_media_type_response(
        self,
        content_type: str | None,
    ) -> JSONResponse:
        """Create 415 Unsupported Media Type response."""
        detail = (
            f"Content-Type '{content_type}' is not supported"
            if content_type
            else "Content-Type header is required"
        )
        return JSONResponse(
            {
                "error": "Unsupported Media Type",
                "detail": detail,
                "allowed_types": self.allowed_types,
            },
            status_code=415,
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request with Content-Type validation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "/")

        # Skip safe methods (GET, HEAD, OPTIONS, TRACE)
        if method in self.safe_methods:
            await self.app(scope, receive, send)
            return

        # Skip excluded paths
        if is_path_excluded(path, self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # Extract Content-Type header
        content_type = extract_header(scope, b"content-type")

        # Check if Content-Type is required
        if content_type is None:
            if self.require_content_type:
                # Check if request has body (Content-Length > 0 or chunked)
                content_length = extract_header(scope, b"content-length")
                transfer_encoding = extract_header(scope, b"transfer-encoding")

                has_body = (content_length and int(content_length) > 0) or (
                    transfer_encoding and "chunked" in transfer_encoding.lower()
                )

                if has_body:
                    response = self._unsupported_media_type_response(None)
                    await response(scope, receive, send)
                    return

            # No body, allow request
            await self.app(scope, receive, send)
            return

        # Validate Content-Type
        if not self._is_allowed(content_type):
            response = self._unsupported_media_type_response(content_type)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
