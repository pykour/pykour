"""Route with explicit HEAD handler for testing."""

from pykour import JSONResponse, Request, Response


async def get(request: Request) -> JSONResponse:
    """GET handler."""
    return JSONResponse({"method": "GET", "message": "Hello from GET"})


async def head(request: Request) -> Response:
    """Explicit HEAD handler."""
    return Response(
        content=b"",
        status_code=200,
        headers={"X-Custom-Head": "explicit-head-handler"},
    )
