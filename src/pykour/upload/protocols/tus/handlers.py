"""HTTP method handlers for tus protocol.

This module provides handler functions that can be used with
TusMiddleware to handle tus protocol requests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pykour.response import Response
from pykour.upload.protocols.tus.exceptions import TusError
from pykour.upload.protocols.tus.headers import build_server_headers

if TYPE_CHECKING:
    from pykour.request import Request
    from pykour.upload.protocols.tus.protocol import TusProtocol


async def handle_options(
    request: "Request",
    protocol: "TusProtocol",
) -> Response:
    """Handle OPTIONS request for server capability discovery.

    Args:
        request: The incoming HTTP request.
        protocol: The tus protocol instance.

    Returns:
        Response with tus capability headers.
    """
    headers = protocol.get_options_headers()
    return Response(
        status_code=204,
        headers=headers,
    )


async def handle_post(
    request: "Request",
    protocol: "TusProtocol",
) -> Response:
    """Handle POST request to create a new upload.

    Args:
        request: The incoming HTTP request.
        protocol: The tus protocol instance.

    Returns:
        Response with Location header pointing to the new upload.
    """
    try:
        result = await protocol.create_upload(request)

        # Build Location URL
        base_url = _get_base_url(request)
        location = protocol.build_location_url(result.upload_id, base_url)

        headers = build_server_headers(
            upload_offset=result.offset,
            location=location,
        )

        return Response(
            status_code=201,
            headers=headers,
        )
    except TusError as e:
        return _error_response(e)


async def handle_head(
    request: "Request",
    protocol: "TusProtocol",
    upload_id: str,
) -> Response:
    """Handle HEAD request to get upload status.

    Args:
        request: The incoming HTTP request.
        protocol: The tus protocol instance.
        upload_id: The upload identifier.

    Returns:
        Response with upload status headers.
    """
    try:
        result = await protocol.get_upload_status(upload_id)

        headers = build_server_headers(
            upload_offset=result.offset,
            upload_length=result.size,
        )

        # Add Cache-Control to prevent caching
        headers["Cache-Control"] = "no-store"

        return Response(
            status_code=200,
            headers=headers,
        )
    except TusError as e:
        return _error_response(e)


async def handle_patch(
    request: "Request",
    protocol: "TusProtocol",
    upload_id: str,
) -> Response:
    """Handle PATCH request to upload a chunk.

    Args:
        request: The incoming HTTP request.
        protocol: The tus protocol instance.
        upload_id: The upload identifier.

    Returns:
        Response with updated offset.
    """
    try:
        result = await protocol.write_chunk(upload_id, request)

        headers = build_server_headers(
            upload_offset=result.offset,
        )

        return Response(
            status_code=204,
            headers=headers,
        )
    except TusError as e:
        return _error_response(e)


async def handle_delete(
    request: "Request",
    protocol: "TusProtocol",
    upload_id: str,
) -> Response:
    """Handle DELETE request to cancel an upload.

    Args:
        request: The incoming HTTP request.
        protocol: The tus protocol instance.
        upload_id: The upload identifier.

    Returns:
        204 No Content response.
    """
    try:
        await protocol.delete_upload(upload_id)

        headers = build_server_headers()

        return Response(
            status_code=204,
            headers=headers,
        )
    except TusError as e:
        return _error_response(e)


def _get_base_url(request: "Request") -> str:
    """Extract base URL from request.

    Args:
        request: The incoming HTTP request.

    Returns:
        Base URL like "https://example.com:8000".
    """
    scheme = request.scheme
    server = request.server
    if server:
        host, port = server
        if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
            return f"{scheme}://{host}"
        return f"{scheme}://{host}:{port}"
    return ""


def _error_response(error: TusError) -> Response:
    """Create error response from TusError.

    Args:
        error: The tus error.

    Returns:
        Response with appropriate status code and headers.
    """
    headers = build_server_headers()
    return Response(
        content=error.message.encode("utf-8"),
        status_code=error.status_code,
        headers=headers,
        media_type="text/plain; charset=utf-8",
    )
