"""Route handlers for root /."""

from pykour import JSONResponse, Request


async def get(request: Request) -> JSONResponse:
    """Root endpoint."""
    return JSONResponse({"message": "Hello, Pykour!"})
