"""tus protocol middleware for Pykour.

This module provides ASGI middleware that handles tus protocol requests
for resumable file uploads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pykour.middleware.base import BaseMiddleware
from pykour.request import Request
from pykour.upload.protocols.tus.exceptions import TusError
from pykour.upload.protocols.tus.handlers import (
    handle_delete,
    handle_head,
    handle_options,
    handle_patch,
    handle_post,
)
from pykour.upload.protocols.tus.headers import TUS_VERSION, build_server_headers
from pykour.upload.protocols.tus.protocol import TusProtocol

if TYPE_CHECKING:
    from pykour.response import Response
    from pykour.types import Receive, Scope, Send
    from pykour.upload.config import TusConfig
    from pykour.upload.storage.base import UploadStorage


class TusMiddleware(BaseMiddleware):
    """ASGI middleware for handling tus protocol requests.

    This middleware intercepts requests to the configured path prefix
    and handles them using the tus protocol. Non-tus requests are
    passed through to the next application.

    Example:
        from pykour import Pykour
        from pykour.upload import TusMiddleware, FileUploadStorage

        app = Pykour()
        app.add_middleware(
            TusMiddleware,
            storage=FileUploadStorage(base_dir="./uploads"),
            path_prefix="/files",
            max_size=100 * 1024 * 1024,
        )

    Or using TusConfig:
        from pykour.upload import TusConfig, TusMiddleware, FileUploadStorage

        config = TusConfig(
            storage=FileUploadStorage(base_dir="./uploads"),
            path_prefix="/files",
        )
        app.add_middleware(TusMiddleware, config=config)
    """

    def __init__(
        self,
        app: Any,
        *,
        config: "TusConfig | None" = None,
        storage: "UploadStorage | None" = None,
        path_prefix: str = "/files",
        max_size: int = 1024 * 1024 * 1024,
        cors_enabled: bool = True,
        cors_origins: list[str] | None = None,
    ) -> None:
        """Initialize tus middleware.

        You can either pass a TusConfig or individual parameters.
        If both are provided, config takes precedence.

        Args:
            app: The next ASGI application in the stack.
            config: Optional TusConfig instance.
            storage: Storage backend (required if config not provided).
            path_prefix: URL path prefix for tus endpoints.
            max_size: Maximum upload size in bytes.
            cors_enabled: Whether to add CORS headers.
            cors_origins: Allowed CORS origins.
        """
        super().__init__(app)

        if config is not None:
            self._storage = config.storage
            self._path_prefix = config.path_prefix
            self._max_size = config.max_size
            self._cors_enabled = config.cors_enabled
            self._cors_origins = config.cors_origins
        else:
            if storage is None:
                raise ValueError("Either config or storage must be provided")
            self._storage = storage
            self._path_prefix = path_prefix.rstrip("/")
            self._max_size = max_size
            self._cors_enabled = cors_enabled
            self._cors_origins = cors_origins or ["*"]

        # Ensure path_prefix starts with /
        if not self._path_prefix.startswith("/"):
            self._path_prefix = "/" + self._path_prefix

        # Create protocol handler
        self._protocol = TusProtocol(
            storage=self._storage,
            max_size=self._max_size,
            path_prefix=self._path_prefix,
        )

    async def __call__(
        self,
        scope: "Scope",
        receive: "Receive",
        send: "Send",
    ) -> None:
        """Handle ASGI request.

        Args:
            scope: ASGI scope dict.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "/")
        method: str = scope.get("method", "GET").upper()

        # Check if this is a tus request
        if not path.startswith(self._path_prefix):
            await self.app(scope, receive, send)
            return

        # Create request object
        request = Request(scope, receive)

        # Handle CORS preflight
        if method == "OPTIONS" and self._cors_enabled:
            response = await handle_options(request, self._protocol)
            await self._send_response(response, send, request)
            return

        # Check for Tus-Resumable header (required for all non-OPTIONS requests)
        if "tus-resumable" not in {k.lower() for k in request.headers.keys()}:
            # Not a tus request, pass through
            await self.app(scope, receive, send)
            return

        # Handle tus request
        try:
            response = await self._handle_tus_request(request, method, path)
        except TusError as e:
            response = self._error_response(e)
        except Exception as e:
            response = self._error_response(TusError(f"Internal server error: {e}"))

        await self._send_response(response, send, request)

    async def _handle_tus_request(
        self,
        request: Request,
        method: str,
        path: str,
    ) -> "Response":
        """Handle a tus protocol request.

        Args:
            request: The incoming HTTP request.
            method: HTTP method.
            path: Request path.

        Returns:
            Response to send.
        """
        from pykour.response import Response

        # Extract upload ID from path
        upload_id = self._extract_upload_id(path)

        if method == "POST" and not upload_id:
            return await handle_post(request, self._protocol)
        elif method == "HEAD" and upload_id:
            return await handle_head(request, self._protocol, upload_id)
        elif method == "PATCH" and upload_id:
            return await handle_patch(request, self._protocol, upload_id)
        elif method == "DELETE" and upload_id:
            return await handle_delete(request, self._protocol, upload_id)
        else:
            return Response(
                content=b"Method not allowed",
                status_code=405,
                headers=build_server_headers(),
                media_type="text/plain",
            )

    def _extract_upload_id(self, path: str) -> str | None:
        """Extract upload ID from request path.

        Args:
            path: Request path like "/files/abc123".

        Returns:
            Upload ID or None if at root path.
        """
        suffix = path[len(self._path_prefix) :].lstrip("/")
        if not suffix:
            return None
        return suffix.split("/")[0]

    def _error_response(self, error: TusError) -> "Response":
        """Create error response from TusError.

        Args:
            error: The tus error.

        Returns:
            Response with appropriate status code.
        """
        from pykour.response import Response

        headers = build_server_headers()
        return Response(
            content=error.message.encode("utf-8"),
            status_code=error.status_code,
            headers=headers,
            media_type="text/plain; charset=utf-8",
        )

    async def _send_response(
        self,
        response: "Response",
        send: "Send",
        request: Request,
    ) -> None:
        """Send response with CORS headers if enabled.

        Args:
            response: The response to send.
            send: ASGI send callable.
            request: The original request (for CORS origin).
        """
        # Build additional headers
        additional_headers: list[tuple[str, str]] = []

        # Add CORS headers if enabled
        if self._cors_enabled:
            origin = request.headers.get("origin", "*")
            if "*" in self._cors_origins or origin in self._cors_origins:
                additional_headers.append(("Access-Control-Allow-Origin", origin))
            else:
                additional_headers.append(
                    ("Access-Control-Allow-Origin", self._cors_origins[0])
                )

            additional_headers.append(
                (
                    "Access-Control-Allow-Methods",
                    "GET, POST, HEAD, PATCH, DELETE, OPTIONS",
                )
            )
            additional_headers.append(
                (
                    "Access-Control-Allow-Headers",
                    "Content-Type, Upload-Length, Upload-Offset, "
                    "Upload-Metadata, Tus-Resumable, Tus-Version, "
                    "Tus-Max-Size, Tus-Extension",
                )
            )
            additional_headers.append(
                (
                    "Access-Control-Expose-Headers",
                    "Upload-Offset, Upload-Length, Location, "
                    "Tus-Resumable, Tus-Version, Tus-Max-Size, Tus-Extension",
                )
            )

        # Add Tus-Resumable header if not present
        existing_header_names = {k for k, v in response.headers}
        if "Tus-Resumable" not in existing_header_names:
            additional_headers.append(("Tus-Resumable", TUS_VERSION))

        # Combine response headers with additional headers
        all_headers = list(response.headers) + additional_headers

        # Send response using ASGI protocol
        headers_list: list[tuple[bytes, bytes]] = [
            (k.encode("latin-1"), v.encode("latin-1")) for k, v in all_headers
        ]

        await send(
            {
                "type": "http.response.start",
                "status": response.status_code,
                "headers": headers_list,
            }
        )

        body = response.body if response.body else b""
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
