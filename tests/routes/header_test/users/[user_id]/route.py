"""Test routes for @header decorator with path parameters."""

from pykour import JSONResponse, Request
from pykour.header import header
from pykour.schema import Path
from pykour.status_code import status_code


@header("X-User-Id", "{user_id}")
async def get(
    request: Request,
    user_id: int = Path(),  # type: ignore[invalid-parameter-default]
) -> JSONResponse:
    """Header with path parameter interpolation."""
    return JSONResponse({"user_id": user_id})


@header("Location", "/users/{user_id}/profile")
@header("X-User-Id", "{user_id}")
@status_code(201)
async def post(
    request: Request,
    user_id: int = Path(),  # type: ignore[invalid-parameter-default]
) -> JSONResponse:
    """Multiple headers with path parameter."""
    return JSONResponse({"created": True, "user_id": user_id})
