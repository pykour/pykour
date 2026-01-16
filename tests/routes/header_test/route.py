"""Test routes for @header decorator."""

from pykour import JSONResponse, Request
from pykour.header import header
from pykour.status_code import status_code


@header("X-API-Version", "1.0")
async def get(request: Request) -> JSONResponse:
    """Static header test."""
    return JSONResponse({"status": "ok"})


@header("Location", "/users/{id}")
@status_code(201)
async def post(request: Request) -> JSONResponse:
    """Dynamic Location header from response body."""
    return JSONResponse({"id": 123, "name": "Alice"})


async def put(request: Request) -> JSONResponse:
    """No header decorator - for comparison."""
    return JSONResponse({"updated": True})


@header("X-Deleted", "true", on_status=204)
@status_code(204)
async def delete(request: Request) -> JSONResponse:
    """Conditional header on 204."""
    return JSONResponse({})
