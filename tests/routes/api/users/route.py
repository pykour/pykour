"""Route handlers for /api/users."""

from pykour import JSONResponse, Request


async def get(request: Request) -> JSONResponse:
    """Get all users."""
    return JSONResponse({"users": [{"id": 1, "name": "Alice"}]})


async def post(request: Request) -> JSONResponse:
    """Create a user."""
    body = await request.body()
    return JSONResponse({"created": True, "body": body.decode()}, status_code=201)
