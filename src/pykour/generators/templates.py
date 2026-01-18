"""Code templates for CRUD generation."""

from __future__ import annotations

# Template for collection route (list + create)
COLLECTION_ROUTE_TEMPLATE = '''\
"""{resource_title} API - List and Create endpoints."""

from pykour import JSONResponse, Request
from pykour.db import Database
from pykour.schema import Body, Query
{schema_import}


async def get(
    request: Request,
    db: Database,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    sort: str | None = Query(default=None),
    order: str = Query(default="asc"),
) -> JSONResponse:
    """List {resource_plural} with pagination."""
    query = db.select("*").from_("{table_name}")

    # Apply sorting
    if sort:
        query = query.order_by(sort, desc=(order == "desc"))

    # Apply pagination
    offset = (page - 1) * limit
    query = query.limit(limit).offset(offset)

    items = await query.fetch_all()
    total = await db.count("{table_name}")

    return JSONResponse({{
        "items": [dict(item) for item in items],
        "page": page,
        "limit": limit,
        "total": total,
    }})


async def post(
    request: Request,
    db: Database,
    data: {create_schema} = Body(),
) -> JSONResponse:
    """Create a new {resource_singular}."""
    values = data.model_dump()

    result = await db.insert("{table_name}").values(**values).returning("*").fetch_one()

    return JSONResponse(dict(result) if result else values, status_code=201)
'''

# Template for item route (get, update, delete)
ITEM_ROUTE_TEMPLATE = '''\
"""{resource_title} API - Get, Update, Delete endpoints."""

from pykour import JSONResponse, Request
from pykour.db import Database
from pykour.schema import Body, Path
{schema_import}


async def get(
    request: Request,
    db: Database,
    {id_field}: {id_type} = Path(),
) -> JSONResponse:
    """Get a {resource_singular} by ID."""
    item = await db.select("*").from_("{table_name}").where({id_field}={id_field}).fetch_one()

    if item is None:
        return JSONResponse({{"error": "Not Found"}}, status_code=404)

    return JSONResponse(dict(item))


async def put(
    request: Request,
    db: Database,
    {id_field}: {id_type} = Path(),
    data: {update_schema} = Body(),
) -> JSONResponse:
    """Update a {resource_singular}."""
    existing = await db.select("*").from_("{table_name}").where({id_field}={id_field}).fetch_one()
    if existing is None:
        return JSONResponse({{"error": "Not Found"}}, status_code=404)

    values = data.model_dump(exclude_unset=True)
    await db.update("{table_name}").set(**values).where({id_field}={id_field}).execute()

    item = await db.select("*").from_("{table_name}").where({id_field}={id_field}).fetch_one()
    return JSONResponse(dict(item) if item else values)


async def delete(
    request: Request,
    db: Database,
    {id_field}: {id_type} = Path(),
) -> JSONResponse:
    """Delete a {resource_singular}."""
    existing = await db.select("*").from_("{table_name}").where({id_field}={id_field}).fetch_one()
    if existing is None:
        return JSONResponse({{"error": "Not Found"}}, status_code=404)

    await db.delete("{table_name}").where({id_field}={id_field}).execute()

    return JSONResponse(None, status_code=204)
'''

# Template for schema file
SCHEMA_TEMPLATE = '''\
"""{resource_title} schemas for validation."""

from pykour.schema import Field, Schema


class Create{resource_pascal}Schema(Schema):
    """{resource_title} creation schema."""

{create_fields}


class Update{resource_pascal}Schema(Schema):
    """{resource_title} update schema."""

{update_fields}
'''

# Template for test file
TEST_TEMPLATE = '''\
"""Tests for {resource_plural} API."""

import pytest

from pykour.testing import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from pykour import Pykour

    app = Pykour(routes_dir="routes")
    return TestClient(app)


class Test{resource_pascal}API:
    """Tests for {resource_plural} CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_{resource_plural}(self, client):
        """Test listing {resource_plural}."""
        response = await client.get("/api/{resource_plural}")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_create_{resource_singular}(self, client):
        """Test creating a {resource_singular}."""
        response = await client.post(
            "/api/{resource_plural}",
            json={{}},  # Add required fields
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_get_{resource_singular}(self, client):
        """Test getting a {resource_singular} by ID."""
        response = await client.get("/api/{resource_plural}/1")
        # Will be 404 if no data
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_update_{resource_singular}(self, client):
        """Test updating a {resource_singular}."""
        response = await client.put(
            "/api/{resource_plural}/1",
            json={{}},  # Add update fields
        )
        assert response.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_delete_{resource_singular}(self, client):
        """Test deleting a {resource_singular}."""
        response = await client.delete("/api/{resource_plural}/1")
        assert response.status_code in (204, 404)
'''

# Template for simple route file (generate route command)
SIMPLE_ROUTE_FILE_TEMPLATE = '''\
"""Route handlers for {path}."""

from pykour import JSONResponse, Request


{handlers}
'''

# Template for simple handler function
SIMPLE_HANDLER_TEMPLATE = '''\
async def {method_lower}(request: Request) -> JSONResponse:
    """{method_upper} {path}"""
    return JSONResponse({{"message": "Hello"}})
'''
