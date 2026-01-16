"""Route handlers for /api/users/[id]."""

from pykour import JSONResponse, Request


async def get(request: Request) -> JSONResponse:
    """Get a user by ID."""
    user_id = request.path_params["id"]
    return JSONResponse({"id": user_id, "name": "Alice"})


async def put(request: Request) -> JSONResponse:
    """Update a user by ID."""
    user_id = request.path_params["id"]
    return JSONResponse({"id": user_id, "updated": True})


async def delete(request: Request) -> JSONResponse:
    """Delete a user by ID."""
    user_id = request.path_params["id"]
    return JSONResponse({"id": user_id, "deleted": True})
