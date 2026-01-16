"""Route handlers for /health."""

from pykour import JSONResponse, Request


async def get(request: Request) -> JSONResponse:
    """Health check endpoint."""
    return JSONResponse({"status": "ok"})
