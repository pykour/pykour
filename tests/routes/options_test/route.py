"""Route with explicit OPTIONS handler for testing."""

from pykour import JSONResponse, Request


async def get(request: Request) -> JSONResponse:
    """GET handler."""
    return JSONResponse({"method": "GET"})


async def options(request: Request) -> JSONResponse:
    """Explicit OPTIONS handler."""
    return JSONResponse(
        {"custom": "options handler", "allowed_methods": ["GET", "OPTIONS"]}
    )
