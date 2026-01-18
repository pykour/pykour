"""User API - List and Create endpoints."""

from typing import Any

from pykour import JSONResponse, Request
from pykour.db import Database


async def get(
    request: Request,
    db: Database,
) -> JSONResponse:
    """List users with pagination."""
    # Extract query parameters (use first value if multiple)
    page_param = request.query_params.get("page", "1")
    page = int(page_param if isinstance(page_param, str) else page_param[0])

    limit_param = request.query_params.get("limit", "20")
    limit = int(limit_param if isinstance(limit_param, str) else limit_param[0])

    sort_param = request.query_params.get("sort")
    sort: str | None = None
    if sort_param:
        sort = sort_param if isinstance(sort_param, str) else sort_param[0]

    order_param = request.query_params.get("order", "asc")
    order = order_param if isinstance(order_param, str) else order_param[0]

    # Validate
    page = max(1, page)
    limit = max(1, min(100, limit))

    query = db.select("*").from_("users")

    # Apply sorting
    if sort:
        query = query.order_by(sort, desc=(order == "desc"))

    # Apply pagination
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)

    items = await query.fetch_all()
    total = await db.count("users")

    return JSONResponse(
        {
            "items": [dict(item) for item in items],
            "page": page,
            "limit": limit,
            "total": total,
        }
    )


async def post(
    request: Request,
    db: Database,
) -> JSONResponse:
    """Create a new user."""
    data: dict[str, Any] = await request.json()

    result = await db.insert("users").values(**data).returning("*").fetch_one()

    return JSONResponse(dict(result) if result else data, status_code=201)
