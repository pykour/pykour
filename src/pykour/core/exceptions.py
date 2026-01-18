"""Exception handling utilities for Pykour."""

from __future__ import annotations

import inspect
import logging
import traceback
from typing import TYPE_CHECKING, Any, cast

from pykour.exception_handlers import ExceptionHandlerRegistry
from pykour.exceptions import HTTPException
from pykour.response import JSONResponse, Response
from pykour.schema import ValidationError

if TYPE_CHECKING:
    from pykour.request import Request


logger = logging.getLogger("pykour")


async def handle_exception(
    request: "Request",
    exc: Exception,
    exception_handlers: ExceptionHandlerRegistry,
    debug: bool,
) -> Response:
    """Handle exceptions during request processing.

    Looks up a registered handler for the exception type (checking MRO).
    If no handler is found, uses the default fallback handler.

    Args:
        request: The request object.
        exc: The exception that was raised.
        exception_handlers: Registry of exception handlers.
        debug: Whether debug mode is enabled.

    Returns:
        Response from the exception handler.
    """
    handler = exception_handlers.get(exc)
    if handler is not None:
        result = handler(request, exc)
        if inspect.isawaitable(result):
            return cast(Response, await result)
        return cast(Response, result)

    # No registered handler - use fallback
    return handle_unhandled_exception(exc, debug)


def handle_http_exception(request: "Request", exc: HTTPException) -> Response:
    """Default handler for HTTPException.

    Args:
        request: The request object.
        exc: The HTTP exception that was raised.

    Returns:
        JSON response with error details.
    """
    content: dict[str, Any] = {"error": exc.detail}

    # Convert headers dict to proper format
    headers: dict[str, str] = {}
    if exc.headers:
        headers.update(exc.headers)

    return JSONResponse(
        content=content,
        status_code=exc.status_code,
        headers=headers,
    )


def handle_validation_exception(request: "Request", exc: ValidationError) -> Response:
    """Default handler for ValidationError.

    Args:
        request: The request object.
        exc: The validation exception that was raised.

    Returns:
        JSON response with validation error details.
    """
    return JSONResponse(
        content=exc.to_dict(),
        status_code=422,
    )


def handle_unhandled_exception(exc: Exception, debug: bool) -> Response:
    """Handle exceptions with no registered handler.

    Args:
        exc: The exception that was raised.
        debug: Whether debug mode is enabled.

    Returns:
        JSON response with error details (verbose in debug mode).
    """
    if debug:
        # In debug mode, show full traceback
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb_str = "".join(tb_lines)
        logger.error(f"Unhandled exception:\n{tb_str}")

        return JSONResponse(
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__,
                "traceback": tb_lines,
            },
            status_code=500,
        )
    else:
        # In production, log the error but return generic message
        logger.exception("Unhandled exception during request processing")
        return JSONResponse(
            content={"error": "Internal Server Error"},
            status_code=500,
        )
