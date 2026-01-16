"""Tests for OpenAPI documentation generation."""

from __future__ import annotations

import pytest

from pykour import Pykour, Schema, Field
from pykour.openapi.config import OpenAPIConfig
from pykour.openapi.generator import OpenAPIGenerator
from pykour.openapi.schema_converter import SchemaConverter
from pykour.router import Router
from tests.helpers import MockSend, create_noop_receive, create_scope


# Module-level schemas for nested schema test (to avoid Python 3.14 get_type_hints issue)
class _AddressSchema(Schema):
    street: str
    city: str


class _PersonSchema(Schema):
    name: str
    address: _AddressSchema


# ---------------------------------------------------------------------------
# Schema Converter Tests
# ---------------------------------------------------------------------------


class TestSchemaConverter:
    """Tests for Schema to JSON Schema conversion."""

    def test_simple_schema(self):
        """Test conversion of a simple schema."""

        class UserSchema(Schema):
            name: str
            age: int

        converter = SchemaConverter()
        result = converter.convert(UserSchema)

        assert result["type"] == "object"
        assert "properties" in result
        assert "name" in result["properties"]
        assert "age" in result["properties"]
        assert result["properties"]["name"]["type"] == "string"
        assert result["properties"]["age"]["type"] == "integer"
        assert set(result["required"]) == {"name", "age"}

    def test_schema_with_constraints(self):
        """Test conversion of schema with field constraints."""

        class ConstrainedSchema(Schema):
            count: int = Field(ge=0, le=100, description="Item count")
            name: str = Field(min_length=1, max_length=50, pattern=r"^[a-z]+$")

        converter = SchemaConverter()
        result = converter.convert(ConstrainedSchema)

        count_prop = result["properties"]["count"]
        assert count_prop["minimum"] == 0
        assert count_prop["maximum"] == 100
        assert count_prop["description"] == "Item count"

        name_prop = result["properties"]["name"]
        assert name_prop["minLength"] == 1
        assert name_prop["maxLength"] == 50
        assert name_prop["pattern"] == r"^[a-z]+$"

    def test_schema_with_optional_fields(self):
        """Test conversion of schema with optional fields."""

        class OptionalSchema(Schema):
            required_field: str
            optional_field: str = Field(default="default")

        converter = SchemaConverter()
        result = converter.convert(OptionalSchema)

        assert "required_field" in result["required"]
        assert "optional_field" not in result.get("required", [])
        assert result["properties"]["optional_field"]["default"] == "default"

    def test_schema_with_list_type(self):
        """Test conversion of schema with list types."""

        class ListSchema(Schema):
            tags: list[str]
            numbers: list[int]

        converter = SchemaConverter()
        result = converter.convert(ListSchema)

        assert result["properties"]["tags"]["type"] == "array"
        assert result["properties"]["tags"]["items"]["type"] == "string"
        assert result["properties"]["numbers"]["items"]["type"] == "integer"

    def test_nested_schema(self):
        """Test conversion of nested schemas."""
        converter = SchemaConverter()
        result = converter.convert(_PersonSchema)

        # Nested schema should create a reference
        assert "$ref" in result["properties"]["address"]
        assert (
            "#/components/schemas/_AddressSchema"
            in result["properties"]["address"]["$ref"]
        )

        # Definition should be collected
        definitions = converter.get_definitions()
        assert "_AddressSchema" in definitions


# ---------------------------------------------------------------------------
# OpenAPI Generator Tests
# ---------------------------------------------------------------------------


class TestOpenAPIGenerator:
    """Tests for OpenAPI schema generation."""

    def test_path_pattern_conversion(self):
        """Test Pykour path pattern to OpenAPI conversion."""
        config = OpenAPIConfig()
        # Create a minimal router for testing
        router = Router("tests/routes")
        generator = OpenAPIGenerator(router, config)

        assert generator._convert_path_pattern("/api/users") == "/api/users"
        assert generator._convert_path_pattern("/api/users/[id]") == "/api/users/{id}"
        assert generator._convert_path_pattern("/docs/[...slug]") == "/docs/{slug}"

    def test_tag_extraction(self):
        """Test automatic tag extraction from paths."""
        config = OpenAPIConfig()
        router = Router("tests/routes")
        generator = OpenAPIGenerator(router, config)

        assert generator._extract_tag("/api/users") == "users"
        assert generator._extract_tag("/api/users/123") == "users"
        assert generator._extract_tag("/health") == "health"
        assert generator._extract_tag("/v1/products") == "products"

    def test_operation_id_generation(self):
        """Test operation ID generation."""
        config = OpenAPIConfig()
        router = Router("tests/routes")
        generator = OpenAPIGenerator(router, config)

        async def custom_handler():
            pass

        # Custom handler name
        assert (
            generator._generate_operation_id("GET", "/api/users", custom_handler)
            == "custom_handler"
        )

        # Standard handler name - generate from path
        async def get():
            pass

        op_id = generator._generate_operation_id("GET", "/api/users", get)
        assert "get" in op_id
        assert "users" in op_id


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestOpenAPIIntegration:
    """Integration tests for OpenAPI with Pykour app."""

    @pytest.mark.asyncio
    async def test_openapi_json_endpoint(self):
        """Test /openapi.json endpoint returns valid schema."""
        app = Pykour(
            routes_dir="tests/routes",
            title="Test API",
            version="2.0.0",
        )

        scope = create_scope(path="/openapi.json")
        receive = create_noop_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        schema = send.json_body
        assert schema["openapi"] == "3.1.0"
        assert schema["info"]["title"] == "Test API"
        assert schema["info"]["version"] == "2.0.0"

    @pytest.mark.asyncio
    async def test_swagger_ui_endpoint(self):
        """Test /docs endpoint returns Swagger UI HTML."""
        app = Pykour(routes_dir="tests/routes")

        scope = create_scope(path="/docs")
        receive = create_noop_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        html = send.body.decode("utf-8")
        assert "swagger-ui" in html
        assert "/openapi.json" in html

    @pytest.mark.asyncio
    async def test_redoc_endpoint(self):
        """Test /redoc endpoint returns ReDoc HTML."""
        app = Pykour(routes_dir="tests/routes")

        scope = create_scope(path="/redoc")
        receive = create_noop_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 200
        html = send.body.decode("utf-8")
        assert "redoc" in html
        assert "/openapi.json" in html

    @pytest.mark.asyncio
    async def test_disabled_docs(self):
        """Test that docs can be disabled."""
        app = Pykour(
            routes_dir="tests/routes",
            docs_url=None,
            openapi_url=None,
            redoc_url=None,
        )

        # Should return 404 for /docs
        scope = create_scope(path="/docs")
        receive = create_noop_receive()
        send = MockSend()

        await app(scope, receive, send)
        assert send.status == 404

    @pytest.mark.asyncio
    async def test_custom_docs_urls(self):
        """Test custom documentation URLs."""
        app = Pykour(
            routes_dir="tests/routes",
            docs_url="/swagger",
            openapi_url="/api/schema.json",
            redoc_url="/documentation",
        )

        # Test custom swagger URL
        scope = create_scope(path="/swagger")
        receive = create_noop_receive()
        send = MockSend()

        await app(scope, receive, send)
        assert send.status == 200
        assert "swagger-ui" in send.body.decode("utf-8")

    def test_openapi_schema_property(self):
        """Test openapi_schema property on Pykour app."""
        app = Pykour(
            routes_dir="tests/routes",
            title="Schema Test API",
        )

        schema = app.openapi_schema
        assert isinstance(schema, dict)
        assert schema["info"]["title"] == "Schema Test API"

    def test_openapi_schema_disabled_raises(self):
        """Test openapi_schema raises when docs disabled."""
        app = Pykour(
            routes_dir="tests/routes",
            docs_url=None,
            openapi_url=None,
            redoc_url=None,
        )

        with pytest.raises(RuntimeError, match="OpenAPI documentation is disabled"):
            _ = app.openapi_schema


# ---------------------------------------------------------------------------
# Config Tests
# ---------------------------------------------------------------------------


class TestOpenAPIConfig:
    """Tests for OpenAPI configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OpenAPIConfig()

        assert config.title == "Pykour API"
        assert config.version == "1.0.0"
        assert config.description is None
        assert config.docs_url == "/docs"
        assert config.openapi_url == "/openapi.json"
        assert config.redoc_url == "/redoc"
        assert config.openapi_version == "3.1.0"

    def test_custom_config(self):
        """Test custom configuration."""
        config = OpenAPIConfig(
            title="My API",
            version="2.0.0",
            description="Test description",
            docs_url="/swagger",
            openapi_url="/schema.json",
            redoc_url=None,
        )

        assert config.title == "My API"
        assert config.version == "2.0.0"
        assert config.description == "Test description"
        assert config.docs_url == "/swagger"
        assert config.openapi_url == "/schema.json"
        assert config.redoc_url is None
