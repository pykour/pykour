"""Test routes for handlers that return None."""

from pykour import Request
from pykour.status_code import status_code


async def delete(request: Request) -> None:
    """DELETE returning None - should return 204 No Content with empty body."""
    # No explicit return means None


@status_code(204)
async def post(request: Request) -> None:
    """POST with explicit 204 returning None."""
    pass


async def get(request: Request) -> None:
    """GET returning None - should return 200 with empty body."""
    return None
