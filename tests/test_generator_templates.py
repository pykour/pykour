"""Tests for code generation templates."""

from __future__ import annotations

import ast


from pykour.generators.templates import (
    COLLECTION_ROUTE_TEMPLATE,
    ITEM_ROUTE_TEMPLATE,
    SCHEMA_TEMPLATE,
    TEST_TEMPLATE,
)


class TestCollectionRouteTemplate:
    """Tests for COLLECTION_ROUTE_TEMPLATE."""

    def test_template_has_get_handler(self) -> None:
        """Template should contain async def get."""
        assert "async def get(" in COLLECTION_ROUTE_TEMPLATE

    def test_template_has_post_handler(self) -> None:
        """Template should contain async def post."""
        assert "async def post(" in COLLECTION_ROUTE_TEMPLATE

    def test_template_uses_placeholders(self) -> None:
        """Template should use format placeholders."""
        assert "{resource_title}" in COLLECTION_ROUTE_TEMPLATE
        assert "{table_name}" in COLLECTION_ROUTE_TEMPLATE
        assert "{create_schema}" in COLLECTION_ROUTE_TEMPLATE
        assert "{resource_plural}" in COLLECTION_ROUTE_TEMPLATE
        assert "{resource_singular}" in COLLECTION_ROUTE_TEMPLATE

    def test_template_format_with_values(self) -> None:
        """Template should format correctly with values."""
        formatted = COLLECTION_ROUTE_TEMPLATE.format(
            resource_title="Users",
            table_name="users",
            create_schema="CreateUserSchema",
            resource_plural="users",
            resource_singular="user",
            schema_import="from schemas import CreateUserSchema",
        )

        assert "Users" in formatted
        assert "users" in formatted
        assert "CreateUserSchema" in formatted

    def test_template_includes_pagination(self) -> None:
        """Template should include page and limit params."""
        assert "page:" in COLLECTION_ROUTE_TEMPLATE
        assert "limit:" in COLLECTION_ROUTE_TEMPLATE
        assert "Query(default=1" in COLLECTION_ROUTE_TEMPLATE
        assert "Query(default=20" in COLLECTION_ROUTE_TEMPLATE

    def test_template_includes_sorting(self) -> None:
        """Template should include sort and order params."""
        assert "sort:" in COLLECTION_ROUTE_TEMPLATE
        assert "order:" in COLLECTION_ROUTE_TEMPLATE

    def test_template_has_database_param(self) -> None:
        """Template should include db: Database parameter."""
        assert "db: Database" in COLLECTION_ROUTE_TEMPLATE

    def test_template_has_request_param(self) -> None:
        """Template should include request: Request parameter."""
        assert "request: Request" in COLLECTION_ROUTE_TEMPLATE


class TestItemRouteTemplate:
    """Tests for ITEM_ROUTE_TEMPLATE."""

    def test_template_has_get_handler(self) -> None:
        """Template should contain async def get."""
        assert "async def get(" in ITEM_ROUTE_TEMPLATE

    def test_template_has_put_handler(self) -> None:
        """Template should contain async def put."""
        assert "async def put(" in ITEM_ROUTE_TEMPLATE

    def test_template_has_delete_handler(self) -> None:
        """Template should contain async def delete."""
        assert "async def delete(" in ITEM_ROUTE_TEMPLATE

    def test_template_uses_placeholders(self) -> None:
        """Template should use format placeholders."""
        assert "{resource_title}" in ITEM_ROUTE_TEMPLATE
        assert "{table_name}" in ITEM_ROUTE_TEMPLATE
        assert "{id_field}" in ITEM_ROUTE_TEMPLATE
        assert "{id_type}" in ITEM_ROUTE_TEMPLATE
        assert "{update_schema}" in ITEM_ROUTE_TEMPLATE

    def test_template_format_with_values(self) -> None:
        """Template should format correctly with values."""
        formatted = ITEM_ROUTE_TEMPLATE.format(
            resource_title="User",
            table_name="users",
            id_field="user_id",
            id_type="int",
            update_schema="UpdateUserSchema",
            resource_singular="user",
            schema_import="from schemas import UpdateUserSchema",
        )

        assert "User" in formatted
        assert "users" in formatted
        assert "user_id" in formatted
        assert "UpdateUserSchema" in formatted

    def test_template_includes_id_param(self) -> None:
        """Template should use id_field and id_type placeholders."""
        assert "{id_field}" in ITEM_ROUTE_TEMPLATE
        assert "{id_type}" in ITEM_ROUTE_TEMPLATE
        assert "= Path()" in ITEM_ROUTE_TEMPLATE

    def test_template_has_404_handling(self) -> None:
        """Template should include 404 Not Found handling."""
        assert "404" in ITEM_ROUTE_TEMPLATE
        assert "Not Found" in ITEM_ROUTE_TEMPLATE


class TestSchemaTemplate:
    """Tests for SCHEMA_TEMPLATE."""

    def test_template_has_create_schema(self) -> None:
        """Template should contain CreateSchema class."""
        assert "class Create{resource_pascal}Schema" in SCHEMA_TEMPLATE

    def test_template_has_update_schema(self) -> None:
        """Template should contain UpdateSchema class."""
        assert "class Update{resource_pascal}Schema" in SCHEMA_TEMPLATE

    def test_template_uses_placeholders(self) -> None:
        """Template should use format placeholders."""
        assert "{resource_title}" in SCHEMA_TEMPLATE
        assert "{resource_pascal}" in SCHEMA_TEMPLATE
        assert "{create_fields}" in SCHEMA_TEMPLATE
        assert "{update_fields}" in SCHEMA_TEMPLATE

    def test_template_format_with_values(self) -> None:
        """Template should format correctly with values."""
        formatted = SCHEMA_TEMPLATE.format(
            resource_title="User",
            resource_pascal="User",
            create_fields="    name: str\n    email: str",
            update_fields="    name: str | None = None\n    email: str | None = None",
        )

        assert "class CreateUserSchema" in formatted
        assert "class UpdateUserSchema" in formatted
        assert "name: str" in formatted

    def test_template_imports_schema(self) -> None:
        """Template should import Schema from pykour."""
        assert "from pykour.schema import" in SCHEMA_TEMPLATE
        assert "Schema" in SCHEMA_TEMPLATE

    def test_template_has_docstrings(self) -> None:
        """Template should include docstrings."""
        assert '"""' in SCHEMA_TEMPLATE


class TestTestTemplate:
    """Tests for TEST_TEMPLATE."""

    def test_template_has_test_class(self) -> None:
        """Template should contain test class."""
        assert "class Test{resource_pascal}API:" in TEST_TEMPLATE

    def test_template_has_list_test(self) -> None:
        """Template should contain test_list_ method."""
        assert "test_list_{resource_plural}" in TEST_TEMPLATE

    def test_template_has_create_test(self) -> None:
        """Template should contain test_create_ method."""
        assert "test_create_{resource_singular}" in TEST_TEMPLATE

    def test_template_has_get_test(self) -> None:
        """Template should contain test_get_ method."""
        assert "test_get_{resource_singular}" in TEST_TEMPLATE

    def test_template_has_update_test(self) -> None:
        """Template should contain test_update_ method."""
        assert "test_update_{resource_singular}" in TEST_TEMPLATE

    def test_template_has_delete_test(self) -> None:
        """Template should contain test_delete_ method."""
        assert "test_delete_{resource_singular}" in TEST_TEMPLATE

    def test_template_format_with_values(self) -> None:
        """Template should format correctly with values."""
        formatted = TEST_TEMPLATE.format(
            resource_title="User",
            resource_pascal="User",
            resource_plural="users",
            resource_singular="user",
        )

        assert "class TestUserAPI:" in formatted
        assert "test_list_users" in formatted
        assert "test_create_user" in formatted

    def test_template_uses_pytest_asyncio(self) -> None:
        """Template should use @pytest.mark.asyncio."""
        assert "@pytest.mark.asyncio" in TEST_TEMPLATE

    def test_template_has_fixture(self) -> None:
        """Template should have client fixture."""
        assert "@pytest.fixture" in TEST_TEMPLATE
        assert "def client(" in TEST_TEMPLATE

    def test_template_imports_pytest(self) -> None:
        """Template should import pytest."""
        assert "import pytest" in TEST_TEMPLATE


class TestTemplateIntegration:
    """Integration tests for templates."""

    def test_collection_template_is_valid_python(self) -> None:
        """Formatted collection template should be valid Python."""
        formatted = COLLECTION_ROUTE_TEMPLATE.format(
            resource_title="Products",
            table_name="products",
            create_schema="CreateProductSchema",
            resource_plural="products",
            resource_singular="product",
            schema_import="from .schemas import CreateProductSchema",
        )

        # Should not raise SyntaxError
        ast.parse(formatted)

    def test_item_template_is_valid_python(self) -> None:
        """Formatted item template should be valid Python."""
        formatted = ITEM_ROUTE_TEMPLATE.format(
            resource_title="Product",
            table_name="products",
            id_field="product_id",
            id_type="int",
            update_schema="UpdateProductSchema",
            resource_singular="product",
            schema_import="from .schemas import UpdateProductSchema",
        )

        # Should not raise SyntaxError
        ast.parse(formatted)

    def test_schema_template_is_valid_python(self) -> None:
        """Formatted schema template should be valid Python."""
        formatted = SCHEMA_TEMPLATE.format(
            resource_title="Product",
            resource_pascal="Product",
            create_fields="    name: str\n    price: float",
            update_fields="    name: str | None = None\n    price: float | None = None",
        )

        # Should not raise SyntaxError
        ast.parse(formatted)

    def test_test_template_is_valid_python(self) -> None:
        """Formatted test template should be valid Python."""
        formatted = TEST_TEMPLATE.format(
            resource_title="Products",
            resource_pascal="Product",
            resource_plural="products",
            resource_singular="product",
        )

        # Should not raise SyntaxError
        ast.parse(formatted)

    def test_all_templates_are_strings(self) -> None:
        """All templates should be string constants."""
        assert isinstance(COLLECTION_ROUTE_TEMPLATE, str)
        assert isinstance(ITEM_ROUTE_TEMPLATE, str)
        assert isinstance(SCHEMA_TEMPLATE, str)
        assert isinstance(TEST_TEMPLATE, str)

    def test_all_templates_non_empty(self) -> None:
        """All templates should be non-empty."""
        assert len(COLLECTION_ROUTE_TEMPLATE) > 0
        assert len(ITEM_ROUTE_TEMPLATE) > 0
        assert len(SCHEMA_TEMPLATE) > 0
        assert len(TEST_TEMPLATE) > 0
