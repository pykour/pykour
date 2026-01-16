"""Exception test routes."""

from pykour import Request
from pykour.response import JSONResponse


async def get(request: Request) -> JSONResponse:
    """Return a simple response."""
    return JSONResponse({"message": "OK"})
