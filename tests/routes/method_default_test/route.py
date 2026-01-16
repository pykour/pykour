"""Test routes for method-based default status codes (no decorator)."""

from pykour import JSONResponse, Request


async def get(request: Request) -> JSONResponse:
    """GET without decorator - should return 200."""
    return JSONResponse({"method": "get"})


async def post(request: Request) -> JSONResponse:
    """POST without decorator - should return 201."""
    return JSONResponse({"method": "post"})


async def put(request: Request) -> JSONResponse:
    """PUT without decorator - should return 200."""
    return JSONResponse({"method": "put"})


async def delete(request: Request) -> JSONResponse:
    """DELETE without decorator - should return 204."""
    return JSONResponse({"method": "delete"})


async def patch(request: Request) -> JSONResponse:
    """PATCH without decorator - should return 200."""
    return JSONResponse({"method": "patch"})
