"""Handler factories for CRUD operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine

from pykour.response import JSONResponse

if TYPE_CHECKING:
    from pykour.crud.config import ListConfig
    from pykour.db.database import Database
    from pykour.db.migrations.table import Table
    from pykour.request import Request
    from pykour.schema.base import Schema

RouteHandler = Callable[..., Coroutine[Any, Any, JSONResponse]]


def create_list_handler(
    table: type[Table],
    config: ListConfig,
) -> RouteHandler:
    """Create a handler for listing items with pagination.

    Args:
        table: Table class for the resource.
        config: List configuration.

    Returns:
        Async handler function.
    """
    tablename = table.get_tablename()
    columns = table.get_columns()
    column_names = list(columns.keys())

    def _get_first(value: str | list[str] | None, default: str = "") -> str:
        """Get the first value from query param (handles list case)."""
        if value is None:
            return default
        if isinstance(value, list):
            return value[0] if value else default
        return value

    async def handler(
        request: Request,
        db: Database,
    ) -> JSONResponse:
        # Get pagination params from query string
        query_params = request.query_params

        page_str = _get_first(query_params.get("page"), "1")
        page = int(page_str) if page_str.isdigit() else 1
        if page < 1:
            page = 1

        limit_str = _get_first(query_params.get("limit"), str(config.default_limit))
        limit = int(limit_str) if limit_str.isdigit() else config.default_limit
        if limit < 1:
            limit = 1
        if limit > config.max_limit:
            limit = config.max_limit

        sort = _get_first(query_params.get("sort"), "")
        order = _get_first(query_params.get("order"), "asc").lower()

        # Build query
        query = db.select("*").from_(tablename)

        # Apply filters from query params (exact match only)
        filterable = config.filterable_fields or column_names
        for col_name in filterable:
            if col_name in column_names:
                value = _get_first(query_params.get(col_name), "")
                if value:
                    query = query.where(**{col_name: value})

        # Apply sorting
        sortable = config.sortable_fields or column_names
        if sort and sort in sortable:
            query = query.order_by(sort, desc=(order == "desc"))

        # Apply pagination
        offset = (page - 1) * limit
        query = query.limit(limit).offset(offset)

        items = await query.fetch_all()
        total = await db.count(tablename)

        return JSONResponse({
            "items": [dict(item) for item in items],
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total > 0 else 0,
        })

    return handler


def create_get_handler(
    table: type[Table],
    id_field: str,
) -> RouteHandler:
    """Create a handler for getting a single item by ID.

    Args:
        table: Table class for the resource.
        id_field: Primary key field name.

    Returns:
        Async handler function.
    """
    tablename = table.get_tablename()

    async def handler(
        request: Request,
        db: Database,
    ) -> JSONResponse:
        # Get ID from path params
        item_id = request.path_params.get(id_field)
        if item_id is None:
            return JSONResponse({"error": "ID not provided"}, status_code=400)

        item = await db.select("*").from_(tablename).where(**{id_field: item_id}).fetch_one()

        if item is None:
            return JSONResponse({"error": "Not Found"}, status_code=404)

        return JSONResponse(dict(item))

    return handler


def create_create_handler(
    table: type[Table],
    schema: type[Schema],
    id_field: str,
) -> RouteHandler:
    """Create a handler for creating a new item.

    Args:
        table: Table class for the resource.
        schema: Schema class for validation.
        id_field: Primary key field name.

    Returns:
        Async handler function.
    """
    tablename = table.get_tablename()

    async def handler(
        request: Request,
        db: Database,
    ) -> JSONResponse:
        # Parse and validate body
        body = await request.json()
        try:
            validated = schema(**body)
            values = validated.model_dump()
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=422)

        # Insert with RETURNING
        query = db.insert(tablename).values(**values).returning("*")
        result = await query.fetch_one()

        if result:
            return JSONResponse(dict(result), status_code=201)
        else:
            # Fallback: fetch the inserted item
            return JSONResponse(values, status_code=201)

    return handler


def create_update_handler(
    table: type[Table],
    schema: type[Schema],
    id_field: str,
) -> RouteHandler:
    """Create a handler for updating an existing item.

    Args:
        table: Table class for the resource.
        schema: Schema class for validation.
        id_field: Primary key field name.

    Returns:
        Async handler function.
    """
    tablename = table.get_tablename()

    async def handler(
        request: Request,
        db: Database,
    ) -> JSONResponse:
        # Get ID from path params
        item_id = request.path_params.get(id_field)
        if item_id is None:
            return JSONResponse({"error": "ID not provided"}, status_code=400)

        # Check if item exists
        existing = await db.select("*").from_(tablename).where(**{id_field: item_id}).fetch_one()
        if existing is None:
            return JSONResponse({"error": "Not Found"}, status_code=404)

        # Parse and validate body
        body = await request.json()
        try:
            validated = schema(**body)
            values = validated.model_dump()
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=422)

        # Update
        await db.update(tablename).set(**values).where(**{id_field: item_id}).execute()

        # Fetch updated item
        item = await db.select("*").from_(tablename).where(**{id_field: item_id}).fetch_one()
        return JSONResponse(dict(item) if item else values)

    return handler


def create_delete_handler(
    table: type[Table],
    id_field: str,
) -> RouteHandler:
    """Create a handler for deleting an item.

    Args:
        table: Table class for the resource.
        id_field: Primary key field name.

    Returns:
        Async handler function.
    """
    tablename = table.get_tablename()

    async def handler(
        request: Request,
        db: Database,
    ) -> JSONResponse:
        # Get ID from path params
        item_id = request.path_params.get(id_field)
        if item_id is None:
            return JSONResponse({"error": "ID not provided"}, status_code=400)

        # Check if item exists
        existing = await db.select("*").from_(tablename).where(**{id_field: item_id}).fetch_one()
        if existing is None:
            return JSONResponse({"error": "Not Found"}, status_code=404)

        # Delete
        await db.delete(tablename).where(**{id_field: item_id}).execute()

        return JSONResponse(None, status_code=204)

    return handler
