"""Catch-all route for testing [...slug] pattern."""

from pykour import JSONResponse, Request


async def get(request: Request) -> JSONResponse:
    """GET handler that returns the catch-all slug parameter."""
    slug = request.path_params["slug"]
    return JSONResponse({"slug": slug, "path": request.path})
