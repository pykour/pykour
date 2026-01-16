"""Route that raises NotFoundException."""

from pykour import NotFoundException, Request
from pykour.response import JSONResponse


async def get(request: Request) -> JSONResponse:
    """Raise NotFoundException."""
    raise NotFoundException(detail="Resource not found")
