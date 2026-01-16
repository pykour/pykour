"""Route handlers for testing required parameters."""

from pykour import JSONResponse, Request


async def get(request: Request, required_param: str) -> JSONResponse:
    """Handler with required parameter (no default, no marker)."""
    return JSONResponse({"param": required_param})
