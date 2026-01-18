"""User API - Get, Update, Delete endpoints."""

from typing import Any

from pykour import JSONResponse, Request
from pykour.db import Database


async def get(
    request: Request,
    db: Database,
) -> JSONResponse:
    """Get a user by ID."""
    user_id = int(request.path_params["id"])
    item = await db.select("*").from_("users").where(id=user_id).fetch_one()

    if item is None:
        return JSONResponse({"error": "Not Found"}, status_code=404)

    return JSONResponse(dict(item))


async def put(
    request: Request,
    db: Database,
) -> JSONResponse:
    """Update a user."""
    user_id = int(request.path_params["id"])
    data: dict[str, Any] = await request.json()

    existing = await db.select("*").from_("users").where(id=user_id).fetch_one()
    if existing is None:
        return JSONResponse({"error": "Not Found"}, status_code=404)

    await db.update("users").set(**data).where(id=user_id).execute()

    item = await db.select("*").from_("users").where(id=user_id).fetch_one()
    return JSONResponse(dict(item) if item else data)


async def delete(
    request: Request,
    db: Database,
) -> JSONResponse:
    """Delete a user."""
    user_id = int(request.path_params["id"])

    existing = await db.select("*").from_("users").where(id=user_id).fetch_one()
    if existing is None:
        return JSONResponse({"error": "Not Found"}, status_code=404)

    await db.delete("users").where(id=user_id).execute()

    return JSONResponse(None, status_code=204)
