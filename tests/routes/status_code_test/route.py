"""Test routes for @status_code decorator."""

from pykour import JSONResponse, Request
from pykour.status_code import status_code


@status_code(201, description="Created")
async def post(request: Request) -> JSONResponse:
    """Create a new resource."""
    return JSONResponse({"created": True})


@status_code(200, description="Success")
@status_code(404, description="Not Found", is_default=False)
async def get(request: Request) -> JSONResponse:
    """Get resource with optional not found."""
    query_params = request.query_params
    if query_params.get("not_found") == "true":
        return JSONResponse({"error": "Not Found"}, status_code=404)
    return JSONResponse({"id": 1})


async def put(request: Request) -> JSONResponse:
    """Update without status_code decorator - should use default 200."""
    return JSONResponse({"updated": True})


@status_code(204, description="No Content")
async def delete(request: Request) -> JSONResponse:
    """Delete resource - dynamic status_code should override declarative."""
    query_params = request.query_params
    if query_params.get("conflict") == "true":
        return JSONResponse({"error": "Conflict"}, status_code=409)
    return JSONResponse({})
