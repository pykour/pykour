"""Tests for CRUD auto-generation module."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pykour.crud.config import CRUDConfig, ListConfig
from pykour.crud.handlers import (
    create_list_handler,
    create_get_handler,
    create_create_handler,
    create_update_handler,
    create_delete_handler,
)
from pykour.crud.registrar import CRUDRegistrar
from pykour.crud.schema_generator import (
    TableSchemaGenerator,
    column_to_field_info,
    column_to_python_type,
    generate_schema_class,
)
from pykour.db.migrations.table import Column, Table
from pykour.db.migrations.types import Boolean, Integer, String
from pykour.schema.base import Schema


class UserTable(Table):
    """Test table for CRUD tests."""

    __tablename__ = "users"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    active = Column(Boolean(), default=True)


class TestListConfig:
    """Tests for ListConfig."""

    def test_default_values(self) -> None:
        config = ListConfig()
        assert config.default_limit == 20
        assert config.max_limit == 100
        assert config.sortable_fields is None
        assert config.filterable_fields is None

    def test_custom_values(self) -> None:
        config = ListConfig(
            default_limit=50,
            max_limit=200,
            sortable_fields=["name", "email"],
            filterable_fields=["active"],
        )
        assert config.default_limit == 50
        assert config.max_limit == 200
        assert config.sortable_fields == ["name", "email"]
        assert config.filterable_fields == ["active"]


class TestCRUDConfig:
    """Tests for CRUDConfig."""

    def test_default_operations(self) -> None:
        config = CRUDConfig(path="/api/users", table=UserTable)
        assert config.operations == ["list", "get", "create", "update", "delete"]

    def test_custom_operations(self) -> None:
        config = CRUDConfig(
            path="/api/users",
            table=UserTable,
            operations=["list", "get"],
        )
        assert config.operations == ["list", "get"]


class TestColumnTypeMapping:
    """Tests for column to Python type mapping."""

    def test_integer_type(self) -> None:
        column = Column(Integer())
        assert column_to_python_type(column) is int

    def test_string_type(self) -> None:
        column = Column(String(100))
        assert column_to_python_type(column) is str

    def test_boolean_type(self) -> None:
        column = Column(Boolean())
        assert column_to_python_type(column) is bool


class TestColumnToFieldInfo:
    """Tests for column to FieldInfo mapping."""

    def test_nullable_column(self) -> None:
        column = Column(String(100), nullable=True)
        field_info = column_to_field_info(column)
        assert field_info.default is None

    def test_non_nullable_column(self) -> None:
        column = Column(String(100), nullable=False)
        field_info = column_to_field_info(column)
        assert not field_info.has_default

    def test_string_length_constraint(self) -> None:
        column = Column(String(50))
        field_info = column_to_field_info(column)
        assert field_info.max_length == 50

    def test_default_value(self) -> None:
        column = Column(Boolean(), default=True)
        field_info = column_to_field_info(column)
        assert field_info.default is True


class TestSchemaGeneration:
    """Tests for schema generation from Table."""

    def test_generate_create_schema(self) -> None:
        schema_cls = generate_schema_class("UserCreate", UserTable, for_create=True)

        assert issubclass(schema_cls, Schema)
        assert schema_cls.__name__ == "UserCreate"

        # id should be excluded (autoincrement)
        fields = schema_cls.__schema_fields__
        assert "id" not in fields
        assert "name" in fields
        assert "email" in fields
        assert "active" in fields

    def test_generate_update_schema(self) -> None:
        schema_cls = generate_schema_class("UserUpdate", UserTable, for_create=False)

        assert issubclass(schema_cls, Schema)
        assert schema_cls.__name__ == "UserUpdate"

        # id is included for update
        fields = schema_cls.__schema_fields__
        assert "id" in fields
        assert "name" in fields
        assert "email" in fields

    def test_exclude_fields(self) -> None:
        schema_cls = generate_schema_class(
            "UserFiltered",
            UserTable,
            exclude_fields=["email"],
            for_create=True,
        )

        fields = schema_cls.__schema_fields__
        assert "email" not in fields
        assert "name" in fields

    def test_readonly_fields(self) -> None:
        schema_cls = generate_schema_class(
            "UserReadonly",
            UserTable,
            readonly_fields=["active"],
            for_create=True,
        )

        fields = schema_cls.__schema_fields__
        assert "active" not in fields
        assert "name" in fields


class TestTableSchemaGenerator:
    """Tests for TableSchemaGenerator class."""

    def test_create_schema_caching(self) -> None:
        generator = TableSchemaGenerator(UserTable)

        schema1 = generator.create_schema
        schema2 = generator.create_schema

        assert schema1 is schema2  # Same instance (cached)

    def test_update_schema_caching(self) -> None:
        generator = TableSchemaGenerator(UserTable)

        schema1 = generator.update_schema
        schema2 = generator.update_schema

        assert schema1 is schema2  # Same instance (cached)

    def test_create_and_update_schema_differ(self) -> None:
        generator = TableSchemaGenerator(UserTable)

        create_schema = generator.create_schema
        update_schema = generator.update_schema

        assert create_schema is not update_schema

        # id should be in update but not in create
        assert "id" not in create_schema.__schema_fields__
        assert "id" in update_schema.__schema_fields__


class TestSchemaValidation:
    """Tests for generated schema validation."""

    def test_valid_data(self) -> None:
        schema_cls = generate_schema_class("UserCreate", UserTable, for_create=True)

        instance = schema_cls(name="Alice", email="alice@example.com", active=True)

        assert instance.name == "Alice"  # type: ignore[attr-defined]
        assert instance.email == "alice@example.com"  # type: ignore[attr-defined]
        assert instance.active is True  # type: ignore[attr-defined]

    def test_model_dump(self) -> None:
        schema_cls = generate_schema_class("UserCreate", UserTable, for_create=True)

        instance = schema_cls(name="Alice", email="alice@example.com")
        data = instance.model_dump()

        assert data["name"] == "Alice"
        assert data["email"] == "alice@example.com"


# ---------------------------------------------------------------------------
# Handler Factory Tests
# ---------------------------------------------------------------------------


class MockRow(dict):
    """Mock database row that supports both dict and attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e


def create_mock_request(
    query_params: dict[str, str] | None = None,
    path_params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock Request object."""
    mock = MagicMock()
    mock.query_params = query_params or {}
    mock.path_params = path_params or {}
    mock.json = AsyncMock(return_value=json_body or {})
    return mock


def create_mock_db(
    select_result: list[dict[str, Any]] | None = None,
    fetch_one_result: dict[str, Any] | None = None,
    count_result: int = 0,
    insert_result: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock Database object with query builder pattern."""
    mock = MagicMock()

    # Mock select chain
    select_mock = MagicMock()
    from_mock = MagicMock()
    where_mock = MagicMock()
    order_by_mock = MagicMock()
    limit_mock = MagicMock()
    offset_mock = MagicMock()

    mock.select.return_value = select_mock
    select_mock.from_.return_value = from_mock
    from_mock.where.return_value = where_mock
    from_mock.order_by.return_value = order_by_mock
    from_mock.limit.return_value = limit_mock

    where_mock.fetch_one = AsyncMock(
        return_value=MockRow(fetch_one_result) if fetch_one_result else None
    )
    where_mock.order_by.return_value = order_by_mock
    where_mock.limit.return_value = limit_mock

    order_by_mock.limit.return_value = limit_mock
    limit_mock.offset.return_value = offset_mock

    # Mock fetch_all to return list of MockRows
    offset_mock.fetch_all = AsyncMock(
        return_value=[MockRow(row) for row in (select_result or [])]
    )

    # Mock count
    mock.count = AsyncMock(return_value=count_result)

    # Mock insert chain
    insert_mock = MagicMock()
    values_mock = MagicMock()
    returning_mock = MagicMock()

    mock.insert.return_value = insert_mock
    insert_mock.values.return_value = values_mock
    values_mock.returning.return_value = returning_mock
    returning_mock.fetch_one = AsyncMock(
        return_value=MockRow(insert_result) if insert_result else None
    )

    # Mock update chain
    update_mock = MagicMock()
    set_mock = MagicMock()
    update_where_mock = MagicMock()

    mock.update.return_value = update_mock
    update_mock.set.return_value = set_mock
    set_mock.where.return_value = update_where_mock
    update_where_mock.execute = AsyncMock()

    # Mock delete chain
    delete_mock = MagicMock()
    delete_where_mock = MagicMock()

    mock.delete.return_value = delete_mock
    delete_mock.where.return_value = delete_where_mock
    delete_where_mock.execute = AsyncMock()

    return mock


def get_response_body(response: Any) -> dict[str, Any]:
    """Helper to get JSON body from response."""
    return json.loads(response.body)


class TestListHandler:
    """Tests for create_list_handler."""

    @pytest.mark.asyncio
    async def test_list_handler_returns_items(self) -> None:
        """Test that list handler returns items with pagination info."""
        config = ListConfig()
        handler = create_list_handler(UserTable, config)

        request = create_mock_request()
        db = create_mock_db(
            select_result=[
                {"id": 1, "name": "Alice", "email": "alice@example.com"},
                {"id": 2, "name": "Bob", "email": "bob@example.com"},
            ],
            count_result=2,
        )

        response = await handler(request, db)

        assert response.status_code == 200
        body = get_response_body(response)
        assert len(body["items"]) == 2
        assert body["page"] == 1
        assert body["limit"] == 20
        assert body["total"] == 2

    @pytest.mark.asyncio
    async def test_list_handler_with_pagination(self) -> None:
        """Test list handler with custom page and limit."""
        config = ListConfig()
        handler = create_list_handler(UserTable, config)

        request = create_mock_request(query_params={"page": "2", "limit": "10"})
        db = create_mock_db(select_result=[], count_result=25)

        response = await handler(request, db)

        assert response.status_code == 200
        body = get_response_body(response)
        assert body["page"] == 2
        assert body["limit"] == 10
        assert body["total"] == 25
        assert body["pages"] == 3

    @pytest.mark.asyncio
    async def test_list_handler_limit_exceeds_max(self) -> None:
        """Test that limit is capped at max_limit."""
        config = ListConfig(max_limit=50)
        handler = create_list_handler(UserTable, config)

        request = create_mock_request(query_params={"limit": "100"})
        db = create_mock_db(select_result=[], count_result=0)

        response = await handler(request, db)

        body = get_response_body(response)
        assert body["limit"] == 50

    @pytest.mark.asyncio
    async def test_list_handler_invalid_page(self) -> None:
        """Test that invalid page defaults to 1."""
        config = ListConfig()
        handler = create_list_handler(UserTable, config)

        request = create_mock_request(query_params={"page": "invalid"})
        db = create_mock_db(select_result=[], count_result=0)

        response = await handler(request, db)

        body = get_response_body(response)
        assert body["page"] == 1

    @pytest.mark.asyncio
    async def test_list_handler_negative_page(self) -> None:
        """Test that negative page defaults to 1."""
        config = ListConfig()
        handler = create_list_handler(UserTable, config)

        request = create_mock_request(query_params={"page": "-1"})
        db = create_mock_db(select_result=[], count_result=0)

        response = await handler(request, db)

        body = get_response_body(response)
        assert body["page"] == 1


class TestGetHandler:
    """Tests for create_get_handler."""

    @pytest.mark.asyncio
    async def test_get_handler_returns_item(self) -> None:
        """Test that get handler returns a single item."""
        handler = create_get_handler(UserTable, "id")

        request = create_mock_request(path_params={"id": 1})
        db = create_mock_db(
            fetch_one_result={"id": 1, "name": "Alice", "email": "alice@example.com"}
        )

        response = await handler(request, db)

        assert response.status_code == 200
        body = get_response_body(response)
        assert body["id"] == 1
        assert body["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_get_handler_not_found(self) -> None:
        """Test that get handler returns 404 when item not found."""
        handler = create_get_handler(UserTable, "id")

        request = create_mock_request(path_params={"id": 999})
        db = create_mock_db(fetch_one_result=None)

        response = await handler(request, db)

        assert response.status_code == 404
        body = get_response_body(response)
        assert "Not Found" in body["error"]

    @pytest.mark.asyncio
    async def test_get_handler_missing_id(self) -> None:
        """Test that get handler returns 400 when ID not provided."""
        handler = create_get_handler(UserTable, "id")

        request = create_mock_request(path_params={})
        db = create_mock_db()

        response = await handler(request, db)

        assert response.status_code == 400
        body = get_response_body(response)
        assert "ID not provided" in body["error"]


class TestCreateHandler:
    """Tests for create_create_handler."""

    @pytest.mark.asyncio
    async def test_create_handler_success(self) -> None:
        """Test that create handler creates a new item."""
        schema_cls = generate_schema_class("UserCreate", UserTable, for_create=True)
        handler = create_create_handler(UserTable, schema_cls, "id")

        request = create_mock_request(
            json_body={"name": "Charlie", "email": "charlie@example.com", "active": True}
        )
        db = create_mock_db(
            insert_result={"id": 3, "name": "Charlie", "email": "charlie@example.com", "active": True}
        )

        response = await handler(request, db)

        assert response.status_code == 201
        body = get_response_body(response)
        assert body["name"] == "Charlie"

    @pytest.mark.asyncio
    async def test_create_handler_validation_error(self) -> None:
        """Test that create handler returns 422 on validation error."""
        schema_cls = generate_schema_class("UserCreate", UserTable, for_create=True)
        handler = create_create_handler(UserTable, schema_cls, "id")

        # Missing required fields
        request = create_mock_request(json_body={})
        db = create_mock_db()

        response = await handler(request, db)

        assert response.status_code == 422
        body = get_response_body(response)
        assert "error" in body

    @pytest.mark.asyncio
    async def test_create_handler_fallback_without_returning(self) -> None:
        """Test create handler fallback when RETURNING is not supported."""
        schema_cls = generate_schema_class("UserCreate", UserTable, for_create=True)
        handler = create_create_handler(UserTable, schema_cls, "id")

        request = create_mock_request(
            json_body={"name": "Dave", "email": "dave@example.com"}
        )
        # No result from RETURNING
        db = create_mock_db(insert_result=None)

        response = await handler(request, db)

        assert response.status_code == 201


class TestUpdateHandler:
    """Tests for create_update_handler."""

    @pytest.mark.asyncio
    async def test_update_handler_success(self) -> None:
        """Test that update handler updates an item."""
        schema_cls = generate_schema_class("UserUpdate", UserTable, for_create=False)
        handler = create_update_handler(UserTable, schema_cls, "id")

        request = create_mock_request(
            path_params={"id": 1},
            json_body={"id": 1, "name": "Alice Updated", "email": "alice@example.com"},
        )
        db = create_mock_db(
            fetch_one_result={"id": 1, "name": "Alice Updated", "email": "alice@example.com"}
        )

        response = await handler(request, db)

        assert response.status_code == 200
        body = get_response_body(response)
        assert body["name"] == "Alice Updated"

    @pytest.mark.asyncio
    async def test_update_handler_not_found(self) -> None:
        """Test that update handler returns 404 when item not found."""
        schema_cls = generate_schema_class("UserUpdate", UserTable, for_create=False)
        handler = create_update_handler(UserTable, schema_cls, "id")

        request = create_mock_request(
            path_params={"id": 999},
            json_body={"id": 999, "name": "Nobody", "email": "nobody@example.com"},
        )
        db = create_mock_db(fetch_one_result=None)

        response = await handler(request, db)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_handler_missing_id(self) -> None:
        """Test that update handler returns 400 when ID not provided."""
        schema_cls = generate_schema_class("UserUpdate", UserTable, for_create=False)
        handler = create_update_handler(UserTable, schema_cls, "id")

        request = create_mock_request(path_params={}, json_body={})
        db = create_mock_db()

        response = await handler(request, db)

        assert response.status_code == 400


class TestDeleteHandler:
    """Tests for create_delete_handler."""

    @pytest.mark.asyncio
    async def test_delete_handler_success(self) -> None:
        """Test that delete handler deletes an item."""
        handler = create_delete_handler(UserTable, "id")

        request = create_mock_request(path_params={"id": 1})
        db = create_mock_db(
            fetch_one_result={"id": 1, "name": "Alice", "email": "alice@example.com"}
        )

        response = await handler(request, db)

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_handler_not_found(self) -> None:
        """Test that delete handler returns 404 when item not found."""
        handler = create_delete_handler(UserTable, "id")

        request = create_mock_request(path_params={"id": 999})
        db = create_mock_db(fetch_one_result=None)

        response = await handler(request, db)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_handler_missing_id(self) -> None:
        """Test that delete handler returns 400 when ID not provided."""
        handler = create_delete_handler(UserTable, "id")

        request = create_mock_request(path_params={})
        db = create_mock_db()

        response = await handler(request, db)

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# CRUDRegistrar Tests
# ---------------------------------------------------------------------------


class TableWithoutPrimaryKey(Table):
    """Test table without primary key."""

    __tablename__ = "no_pk"

    name = Column(String(100), nullable=False)


class TestCRUDRegistrar:
    """Tests for CRUDRegistrar class."""

    def test_register_all_operations(self) -> None:
        """Test registering all CRUD operations."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        registrar.register("/api/users", UserTable)

        # Should register collection and item routes
        assert mock_app.register_route.call_count == 2

        # Get the call arguments
        calls = mock_app.register_route.call_args_list

        # First call should be collection routes
        collection_path, collection_handlers = calls[0][0]
        assert collection_path == "/api/users"
        assert "GET" in collection_handlers
        assert "POST" in collection_handlers

        # Second call should be item routes
        item_path, item_handlers = calls[1][0]
        assert item_path == "/api/users/[id]"
        assert "GET" in item_handlers
        assert "PUT" in item_handlers
        assert "DELETE" in item_handlers

    def test_register_only_list_and_get(self) -> None:
        """Test registering only list and get operations."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        registrar.register("/api/users", UserTable, operations=["list", "get"])

        assert mock_app.register_route.call_count == 2

        calls = mock_app.register_route.call_args_list

        # Collection routes should only have GET (list)
        collection_path, collection_handlers = calls[0][0]
        assert "GET" in collection_handlers
        assert "POST" not in collection_handlers

        # Item routes should only have GET
        item_path, item_handlers = calls[1][0]
        assert "GET" in item_handlers
        assert "PUT" not in item_handlers
        assert "DELETE" not in item_handlers

    def test_register_only_create(self) -> None:
        """Test registering only create operation."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        registrar.register("/api/users", UserTable, operations=["create"])

        # Only collection routes should be registered
        assert mock_app.register_route.call_count == 1

        path, handlers = mock_app.register_route.call_args[0]
        assert path == "/api/users"
        assert "POST" in handlers
        assert "GET" not in handlers

    def test_register_only_item_operations(self) -> None:
        """Test registering only get, update, delete operations."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        registrar.register(
            "/api/users", UserTable, operations=["get", "update", "delete"]
        )

        # Only item routes should be registered
        assert mock_app.register_route.call_count == 1

        path, handlers = mock_app.register_route.call_args[0]
        assert path == "/api/users/[id]"
        assert "GET" in handlers
        assert "PUT" in handlers
        assert "DELETE" in handlers

    def test_register_with_custom_id_field(self) -> None:
        """Test registering with custom id_field."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        registrar.register(
            "/api/users", UserTable, operations=["get"], id_field="user_id"
        )

        path, _ = mock_app.register_route.call_args[0]
        assert path == "/api/users/[user_id]"

    def test_detect_id_field_auto(self) -> None:
        """Test automatic id_field detection."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        # UserTable has 'id' as primary key
        detected = registrar._detect_id_field(UserTable)
        assert detected == "id"

    def test_detect_id_field_no_primary_key(self) -> None:
        """Test that ValueError is raised when no primary key is found."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        with pytest.raises(ValueError) as exc_info:
            registrar._detect_id_field(TableWithoutPrimaryKey)

        assert "no primary key column" in str(exc_info.value)

    def test_register_with_list_config(self) -> None:
        """Test registering with custom list config."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        list_config = ListConfig(default_limit=50, max_limit=200)
        registrar.register(
            "/api/users", UserTable, operations=["list"], list_config=list_config
        )

        # Just ensure it doesn't raise an error
        assert mock_app.register_route.call_count == 1

    def test_register_with_exclude_fields(self) -> None:
        """Test registering with exclude_fields."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        registrar.register(
            "/api/users",
            UserTable,
            operations=["create"],
            exclude_fields=["email"],
        )

        # Just ensure it doesn't raise an error
        assert mock_app.register_route.call_count == 1

    def test_register_with_readonly_fields(self) -> None:
        """Test registering with readonly_fields."""
        mock_app = MagicMock()
        registrar = CRUDRegistrar(mock_app)

        registrar.register(
            "/api/users",
            UserTable,
            operations=["update"],
            readonly_fields=["active"],
        )

        # Just ensure it doesn't raise an error
        assert mock_app.register_route.call_count == 1
