"""Route handlers for /."""

from pykour import JSONResponse, Request


async def get(request: Request) -> JSONResponse:
    """Index endpoint."""
    return JSONResponse({"message": "Hello, Pykour!"})
