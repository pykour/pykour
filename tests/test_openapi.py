"""Tests for OpenAPI documentation generation."""

from __future__ import annotations

import json

import pytest

from pykour import Pykour, Schema, Field
from pykour.openapi.models import (
    ContactObject,
    LicenseObject,
    InfoObject,
    ServerObject,
    ExternalDocumentationObject,
    TagObject,
    ReferenceObject,
    SchemaObject,
    ExampleObject,
    EncodingObject,
    MediaTypeObject,
    ParameterObject,
    RequestBodyObject,
    HeaderObject,
    LinkObject,
    ResponseObject,
    OperationObject,
    PathItemObject,
    ComponentsObject,
    OpenAPIDocument,
)
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


# ---------------------------------------------------------------------------
# OpenAPI Models (TypedDict) Tests
# ---------------------------------------------------------------------------


class TestOpenAPIModels:
    """Tests for OpenAPI TypedDict models."""

    def test_contact_object_instantiation(self) -> None:
        """Test ContactObject can be instantiated."""
        contact: ContactObject = {
            "name": "API Support",
            "url": "https://example.com/support",
            "email": "support@example.com",
        }
        assert contact["name"] == "API Support"
        assert contact["url"] == "https://example.com/support"
        assert contact["email"] == "support@example.com"

    def test_license_object_instantiation(self) -> None:
        """Test LicenseObject can be instantiated."""
        license_obj: LicenseObject = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        }
        assert license_obj["name"] == "MIT"

    def test_info_object_with_nested_objects(self) -> None:
        """Test InfoObject with nested ContactObject and LicenseObject."""
        info: InfoObject = {
            "title": "Test API",
            "version": "1.0.0",
            "description": "A test API",
            "contact": {"name": "Test", "email": "test@example.com"},
            "license": {"name": "MIT"},
        }
        assert info["title"] == "Test API"
        assert info["contact"]["name"] == "Test"
        assert info["license"]["name"] == "MIT"

    def test_server_object_with_variables(self) -> None:
        """Test ServerObject with ServerVariableObject."""
        server: ServerObject = {
            "url": "https://{environment}.api.example.com",
            "description": "API Server",
            "variables": {
                "environment": {
                    "default": "production",
                    "enum": ["production", "staging", "development"],
                    "description": "Server environment",
                }
            },
        }
        assert server["url"] == "https://{environment}.api.example.com"
        assert server["variables"]["environment"]["default"] == "production"

    def test_schema_object_with_constraints(self) -> None:
        """Test SchemaObject with various constraints."""
        schema: SchemaObject = {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "minimum": 1},
                "name": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 100,
                    "pattern": "^[a-zA-Z]+$",
                },
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["id", "name"],
        }
        assert schema["type"] == "object"
        assert schema["properties"]["id"]["minimum"] == 1
        assert schema["properties"]["name"]["maxLength"] == 100
        assert schema["required"] == ["id", "name"]

    def test_parameter_object_instantiation(self) -> None:
        """Test ParameterObject for various parameter types."""
        path_param: ParameterObject = {
            "name": "id",
            "required": True,
            "schema": {"type": "integer"},
            "description": "User ID",
        }
        query_param: ParameterObject = {
            "name": "filter",
            "required": False,
            "schema": {"type": "string"},
        }
        assert path_param["name"] == "id"
        assert path_param["required"] is True
        assert query_param["required"] is False

    def test_request_body_object_instantiation(self) -> None:
        """Test RequestBodyObject with content."""
        request_body: RequestBodyObject = {
            "description": "User data",
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    }
                }
            },
        }
        assert request_body["required"] is True
        assert "application/json" in request_body["content"]

    def test_response_object_instantiation(self) -> None:
        """Test ResponseObject with headers and content."""
        response: ResponseObject = {
            "description": "Successful response",
            "headers": {
                "X-Rate-Limit": {
                    "schema": {"type": "integer"},
                    "description": "Rate limit",
                }
            },
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"data": {"type": "array"}},
                    }
                }
            },
        }
        assert response["description"] == "Successful response"
        assert "X-Rate-Limit" in response["headers"]

    def test_operation_object_instantiation(self) -> None:
        """Test OperationObject with full structure."""
        operation: OperationObject = {
            "tags": ["users"],
            "summary": "Get user by ID",
            "description": "Returns a single user",
            "operationId": "getUserById",
            "parameters": [
                {"name": "id", "required": True, "schema": {"type": "integer"}}
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                },
                "404": {"description": "User not found"},
            },
            "deprecated": False,
        }
        assert operation["tags"] == ["users"]
        assert operation["operationId"] == "getUserById"
        assert "200" in operation["responses"]

    def test_path_item_object_with_operations(self) -> None:
        """Test PathItemObject with multiple HTTP methods."""
        path_item: PathItemObject = {
            "summary": "User operations",
            "get": {
                "summary": "List users",
                "responses": {"200": {"description": "OK"}},
            },
            "post": {
                "summary": "Create user",
                "requestBody": {"content": {"application/json": {"schema": {}}}},
                "responses": {"201": {"description": "Created"}},
            },
        }
        assert path_item["get"]["summary"] == "List users"
        assert path_item["post"]["summary"] == "Create user"

    def test_components_object_instantiation(self) -> None:
        """Test ComponentsObject with schemas and security schemes."""
        components: ComponentsObject = {
            "schemas": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                },
                "Error": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                },
            },
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
        }
        assert "User" in components["schemas"]
        assert "bearerAuth" in components["securitySchemes"]

    def test_openapi_document_full_structure(self) -> None:
        """Test complete OpenAPIDocument structure."""
        doc: OpenAPIDocument = {
            "openapi": "3.1.0",
            "info": {
                "title": "Test API",
                "version": "1.0.0",
                "description": "A comprehensive test API",
                "contact": {"name": "Support", "email": "support@test.com"},
            },
            "servers": [
                {"url": "https://api.example.com", "description": "Production"}
            ],
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "responses": {"200": {"description": "OK"}},
                    }
                }
            },
            "components": {
                "schemas": {
                    "User": {
                        "type": "object",
                        "properties": {"id": {"type": "integer"}},
                    }
                }
            },
            "tags": [{"name": "users", "description": "User operations"}],
        }
        assert doc["openapi"] == "3.1.0"
        assert doc["info"]["title"] == "Test API"
        assert "/users" in doc["paths"]

    def test_openapi_document_json_serialization(self) -> None:
        """Test OpenAPIDocument can be serialized to JSON and back."""
        doc: OpenAPIDocument = {
            "openapi": "3.1.0",
            "info": {"title": "Serialization Test", "version": "1.0.0"},
            "paths": {
                "/test": {"get": {"responses": {"200": {"description": "Success"}}}}
            },
        }
        json_str = json.dumps(doc)
        parsed = json.loads(json_str)

        assert parsed["openapi"] == "3.1.0"
        assert parsed["info"]["title"] == "Serialization Test"
        assert "/test" in parsed["paths"]

    def test_external_documentation_object(self) -> None:
        """Test ExternalDocumentationObject."""
        ext_doc: ExternalDocumentationObject = {
            "description": "Find more info here",
            "url": "https://docs.example.com",
        }
        assert ext_doc["url"] == "https://docs.example.com"

    def test_tag_object_with_external_docs(self) -> None:
        """Test TagObject with ExternalDocumentationObject."""
        tag: TagObject = {
            "name": "users",
            "description": "User management operations",
            "externalDocs": {
                "description": "User API documentation",
                "url": "https://docs.example.com/users",
            },
        }
        assert tag["name"] == "users"
        assert tag["externalDocs"]["url"] == "https://docs.example.com/users"

    def test_example_object_instantiation(self) -> None:
        """Test ExampleObject."""
        example: ExampleObject = {
            "summary": "A sample user",
            "value": {"id": 1, "name": "John Doe"},
        }
        assert example["summary"] == "A sample user"
        assert example["value"]["id"] == 1

    def test_header_object_instantiation(self) -> None:
        """Test HeaderObject."""
        header: HeaderObject = {
            "description": "Rate limit header",
            "required": False,
            "schema": {"type": "integer"},
        }
        assert header["description"] == "Rate limit header"

    def test_link_object_instantiation(self) -> None:
        """Test LinkObject."""
        link: LinkObject = {
            "operationId": "getUser",
            "parameters": {"userId": "$response.body#/id"},
            "description": "Link to get user details",
        }
        assert link["operationId"] == "getUser"

    def test_encoding_object_instantiation(self) -> None:
        """Test EncodingObject for multipart."""
        encoding: EncodingObject = {
            "contentType": "image/png",
            "style": "form",
            "explode": True,
        }
        assert encoding["contentType"] == "image/png"

    def test_media_type_object_with_examples(self) -> None:
        """Test MediaTypeObject with multiple examples."""
        media_type: MediaTypeObject = {
            "schema": {"type": "object", "properties": {"name": {"type": "string"}}},
            "examples": {
                "user1": {"value": {"name": "Alice"}},
                "user2": {"value": {"name": "Bob"}},
            },
        }
        assert "user1" in media_type["examples"]
        assert media_type["examples"]["user2"]["value"]["name"] == "Bob"

    def test_empty_reference_object(self) -> None:
        """Test ReferenceObject can be instantiated (even if empty)."""
        ref: ReferenceObject = {}
        assert isinstance(ref, dict)

    def test_schema_object_with_composition(self) -> None:
        """Test SchemaObject with allOf, oneOf, anyOf."""
        schema_allof: SchemaObject = {
            "allOf": [
                {"type": "object", "properties": {"id": {"type": "integer"}}},
                {"type": "object", "properties": {"name": {"type": "string"}}},
            ]
        }
        schema_oneof: SchemaObject = {
            "oneOf": [{"type": "string"}, {"type": "integer"}]
        }
        schema_anyof: SchemaObject = {"anyOf": [{"type": "string"}, {"type": "null"}]}

        assert len(schema_allof["allOf"]) == 2
        assert len(schema_oneof["oneOf"]) == 2
        assert len(schema_anyof["anyOf"]) == 2
