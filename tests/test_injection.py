"""Unit tests for the ParameterInjector and body parsers."""

from __future__ import annotations

import dataclasses

import pytest

from pykour.di import Depends, ServiceContainer
from pykour.injection import (
    ParameterInjector,
    SchemaBodyParser,
    DictBodyParser,
    DataclassBodyParser,
    PrimitiveBodyParser,
    ListBodyParser,
)
from pykour.schema import Body, Field, Path, Query, Schema, ValidationError
from pykour.request import Request
from tests.helpers import create_receive, create_scope


# =============================================================================
# Test Schema classes (defined at module level to support annotations)
# =============================================================================


class UserSchema(Schema):
    """Test schema for user data."""

    name: str
    age: int


class UserSchemaWithValidation(Schema):
    """Test schema with validation constraint."""

    name: str
    age: int = Field(ge=0)


class CreateUserSchema(Schema):
    """Test schema for creating users."""

    name: str


@dataclasses.dataclass
class UserDataclass:
    """Test dataclass for user data."""

    name: str
    age: int


# =============================================================================
# Test fixtures
# =============================================================================


@pytest.fixture
def services() -> ServiceContainer:
    """Create a fresh ServiceContainer for testing."""
    return ServiceContainer()


@pytest.fixture
def injector(services: ServiceContainer) -> ParameterInjector:
    """Create a ParameterInjector for testing."""
    return ParameterInjector(services)


def create_request(
    path: str = "/",
    method: str = "GET",
    query_string: str = "",
    body: bytes = b"",
) -> Request:
    """Create a Request object for testing."""
    # query_string must be bytes for ASGI scope
    query_bytes = query_string.encode("utf-8") if query_string else b""
    scope = create_scope(path=path, method=method, query_string=query_bytes)
    receive = create_receive(body)
    return Request(scope, receive, {})


# =============================================================================
# Body Parser Tests
# =============================================================================


class TestSchemaBodyParser:
    """Tests for SchemaBodyParser."""

    def test_can_parse_schema(self) -> None:
        """Schema subclasses should be parseable."""
        parser = SchemaBodyParser()
        assert parser.can_parse(UserSchema) is True

    def test_cannot_parse_non_schema(self) -> None:
        """Non-Schema types should not be parseable."""
        parser = SchemaBodyParser()
        assert parser.can_parse(dict) is False
        assert parser.can_parse(str) is False
        assert parser.can_parse(int) is False

    def test_parse_valid_schema(self) -> None:
        """Valid data should parse to Schema instance."""
        parser = SchemaBodyParser()
        result = parser.parse("user", UserSchema, {"name": "Alice", "age": 30})

        assert isinstance(result, UserSchema)
        assert result.name == "Alice"
        assert result.age == 30

    def test_parse_invalid_schema_raises(self) -> None:
        """Invalid data should raise ValidationError."""
        parser = SchemaBodyParser()

        with pytest.raises(ValidationError):
            parser.parse("user", UserSchemaWithValidation, {"name": "Alice", "age": -1})


class TestDictBodyParser:
    """Tests for DictBodyParser."""

    def test_can_parse_dict(self) -> None:
        """dict type should be parseable."""
        parser = DictBodyParser()
        assert parser.can_parse(dict) is True

    def test_cannot_parse_other_types(self) -> None:
        """Non-dict types should not be parseable."""
        parser = DictBodyParser()
        assert parser.can_parse(list) is False
        assert parser.can_parse(str) is False

    def test_parse_dict(self) -> None:
        """Body data should be returned as-is for dict type."""
        parser = DictBodyParser()
        data = {"key": "value", "nested": {"a": 1}}
        result = parser.parse("body", dict, data)
        assert result == data


class TestDataclassBodyParser:
    """Tests for DataclassBodyParser."""

    def test_can_parse_dataclass(self) -> None:
        """Dataclass types should be parseable."""
        parser = DataclassBodyParser()
        assert parser.can_parse(UserDataclass) is True

    def test_cannot_parse_non_dataclass(self) -> None:
        """Non-dataclass types should not be parseable."""
        parser = DataclassBodyParser()
        assert parser.can_parse(dict) is False

        class RegularClass:
            pass

        assert parser.can_parse(RegularClass) is False

    def test_parse_dataclass(self) -> None:
        """Valid data should parse to dataclass instance."""
        parser = DataclassBodyParser()
        result = parser.parse("user", UserDataclass, {"name": "Bob", "age": 25})

        assert isinstance(result, UserDataclass)
        assert result.name == "Bob"
        assert result.age == 25

    def test_parse_invalid_dataclass_raises(self) -> None:
        """Invalid data should raise ValidationError."""
        parser = DataclassBodyParser()

        with pytest.raises(ValidationError):
            parser.parse("user", UserDataclass, {"name": "Bob"})  # Missing 'age'


class TestPrimitiveBodyParser:
    """Tests for PrimitiveBodyParser."""

    def test_can_parse_primitives(self) -> None:
        """Primitive types should be parseable."""
        parser = PrimitiveBodyParser()
        assert parser.can_parse(int) is True
        assert parser.can_parse(float) is True
        assert parser.can_parse(str) is True
        assert parser.can_parse(bool) is True

    def test_cannot_parse_non_primitives(self) -> None:
        """Non-primitive types should not be parseable."""
        parser = PrimitiveBodyParser()
        assert parser.can_parse(dict) is False
        assert parser.can_parse(list) is False

    def test_parse_int(self) -> None:
        """Integer body should be parsed correctly."""
        parser = PrimitiveBodyParser()
        assert parser.parse("count", int, 42) == 42
        assert parser.parse("count", int, "42") == 42

    def test_parse_float(self) -> None:
        """Float body should be parsed correctly."""
        parser = PrimitiveBodyParser()
        assert parser.parse("value", float, 3.14) == 3.14
        assert parser.parse("value", float, "3.14") == 3.14

    def test_parse_str(self) -> None:
        """String body should be parsed correctly."""
        parser = PrimitiveBodyParser()
        assert parser.parse("text", str, "hello") == "hello"

    def test_parse_bool(self) -> None:
        """Boolean body should be parsed correctly."""
        parser = PrimitiveBodyParser()
        assert parser.parse("flag", bool, True) is True
        assert parser.parse("flag", bool, False) is False

    def test_parse_invalid_raises(self) -> None:
        """Invalid type coercion should raise ValidationError."""
        parser = PrimitiveBodyParser()
        with pytest.raises(ValidationError):
            parser.parse("count", int, "not_a_number")


class TestListBodyParser:
    """Tests for ListBodyParser."""

    def test_can_parse_list(self) -> None:
        """list type should be parseable."""
        parser = ListBodyParser()
        assert parser.can_parse(list) is True

    def test_cannot_parse_non_list(self) -> None:
        """Non-list types should not be parseable."""
        parser = ListBodyParser()
        assert parser.can_parse(dict) is False
        assert parser.can_parse(tuple) is False

    def test_parse_list(self) -> None:
        """List body should be returned correctly."""
        parser = ListBodyParser()
        data = [1, 2, 3]
        result = parser.parse("items", list, data)
        assert result == data

    def test_parse_non_list_raises(self) -> None:
        """Non-list data should raise ValidationError."""
        parser = ListBodyParser()
        with pytest.raises(ValidationError):
            parser.parse("items", list, {"not": "a list"})


# =============================================================================
# ParameterInjector Tests
# =============================================================================


class TestParameterInjectorServiceDepends:
    """Tests for service dependency injection."""

    def test_inject_registered_service(self, services: ServiceContainer) -> None:
        """Registered services should be injected."""

        class MyService:
            def get_value(self) -> str:
                return "test"

        services.register(MyService)
        injector = ParameterInjector(services)

        result = injector.inject_service_depends("svc", MyService, Depends())
        assert isinstance(result, MyService)
        assert result.get_value() == "test"

    def test_inject_service_with_explicit_type(
        self, services: ServiceContainer
    ) -> None:
        """Explicit dependency type in Depends should be used."""

        class Interface:
            pass

        class Implementation(Interface):
            pass

        services.register(Interface, Implementation)
        injector = ParameterInjector(services)

        result = injector.inject_service_depends("svc", object, Depends(Interface))
        assert isinstance(result, Implementation)

    def test_inject_unregistered_service_raises(
        self, services: ServiceContainer
    ) -> None:
        """Unregistered services should raise exception."""
        from pykour.di import ServiceNotFoundException

        injector = ParameterInjector(services)

        class UnknownService:
            pass

        with pytest.raises(ServiceNotFoundException):
            injector.inject_service_depends("svc", UnknownService, Depends())


class TestParameterInjectorPathParam:
    """Tests for path parameter injection."""

    def test_inject_existing_path_param(self, injector: ParameterInjector) -> None:
        """Existing path params should be coerced to correct type."""
        result = injector.inject_path_param(
            "id", int, Path(), {"id": "42", "name": "test"}
        )
        assert result == 42

    def test_inject_path_param_with_default(self, injector: ParameterInjector) -> None:
        """Missing path param with default should return default."""
        result = injector.inject_path_param("id", int, Path(default=99), {})
        assert result == 99

    def test_inject_missing_required_path_param_raises(
        self, injector: ParameterInjector
    ) -> None:
        """Missing required path param should raise ValidationError."""
        with pytest.raises(ValidationError):
            injector.inject_path_param("id", int, Path(), {})


class TestParameterInjectorQueryParam:
    """Tests for query parameter injection."""

    def test_inject_existing_query_param(self, injector: ParameterInjector) -> None:
        """Existing query params should be coerced to correct type."""
        result = injector.inject_query_param("page", int, Query(), {"page": "5"})
        assert result == 5

    def test_inject_query_param_with_default(self, injector: ParameterInjector) -> None:
        """Missing query param with default should return default."""
        result = injector.inject_query_param("page", int, Query(default=1), {})
        assert result == 1

    def test_inject_query_param_with_alias(self, injector: ParameterInjector) -> None:
        """Query param alias should be used for lookup."""
        result = injector.inject_query_param(
            "page_number", int, Query(alias="page"), {"page": "10"}
        )
        assert result == 10

    def test_inject_missing_required_query_param_raises(
        self, injector: ParameterInjector
    ) -> None:
        """Missing required query param should raise ValidationError."""
        with pytest.raises(ValidationError):
            injector.inject_query_param("page", int, Query(), {})


class TestParameterInjectorConventionQuery:
    """Tests for convention-based query parameter injection."""

    def test_inject_convention_query_int(self, injector: ParameterInjector) -> None:
        """Convention query params should be coerced to int."""
        result = injector.inject_convention_query("count", int, "42")
        assert result == 42

    def test_inject_convention_query_str(self, injector: ParameterInjector) -> None:
        """Convention query params should work with str."""
        result = injector.inject_convention_query("name", str, "Alice")
        assert result == "Alice"

    def test_inject_convention_query_invalid_raises(
        self, injector: ParameterInjector
    ) -> None:
        """Invalid type coercion should raise ValidationError."""
        with pytest.raises(ValidationError):
            injector.inject_convention_query("count", int, "not_an_int")


class TestParameterInjectorBodyParam:
    """Tests for body parameter injection."""

    @pytest.mark.asyncio
    async def test_inject_body_dict(self, injector: ParameterInjector) -> None:
        """Dict body params should return parsed JSON."""
        request = create_request(body=b'{"key": "value"}')
        result, body_data = await injector.inject_body_param(
            "data", dict, request, None
        )
        assert result == {"key": "value"}
        assert body_data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_inject_body_schema(self, injector: ParameterInjector) -> None:
        """Schema body params should return validated instance."""
        request = create_request(body=b'{"name": "Alice", "age": 30}')
        result, body_data = await injector.inject_body_param(
            "user", UserSchema, request, None
        )

        assert isinstance(result, UserSchema)
        assert result.name == "Alice"
        assert result.age == 30

    @pytest.mark.asyncio
    async def test_inject_body_with_cached_data(
        self, injector: ParameterInjector
    ) -> None:
        """Body data should be reused from cache."""
        request = create_request(body=b"should_not_be_read")
        cached_data = {"cached": True}

        result, body_data = await injector.inject_body_param(
            "data", dict, request, cached_data
        )

        assert result == {"cached": True}
        assert body_data == cached_data

    @pytest.mark.asyncio
    async def test_inject_body_malformed_json_raises(
        self, injector: ParameterInjector
    ) -> None:
        """Malformed JSON should raise ValidationError."""
        request = create_request(body=b"not valid json")

        with pytest.raises(ValidationError) as exc_info:
            await injector.inject_body_param("data", dict, request, None)

        assert exc_info.value.errors[0].type == "value_error.jsondecode"


class TestParameterInjectorInject:
    """Integration tests for the inject method."""

    @pytest.mark.asyncio
    async def test_inject_request_param(self, injector: ParameterInjector) -> None:
        """Request param should be injected automatically."""

        async def handler(request: Request) -> dict:
            return {"path": request.path}

        request = create_request(path="/test")
        kwargs = await injector.inject(handler, request, {})

        assert "request" in kwargs
        assert kwargs["request"] is request

    @pytest.mark.asyncio
    async def test_inject_path_params(self, injector: ParameterInjector) -> None:
        """Path params should be injected with correct types."""

        async def handler(user_id: int = Path()) -> dict:
            return {"user_id": user_id}

        request = create_request(path="/users/42")
        kwargs = await injector.inject(handler, request, {"user_id": "42"})

        assert kwargs["user_id"] == 42

    @pytest.mark.asyncio
    async def test_inject_query_params(self, injector: ParameterInjector) -> None:
        """Query params should be injected with correct types."""

        async def handler(page: int = Query(default=1)) -> dict:
            return {"page": page}

        request = create_request(query_string="page=5")
        kwargs = await injector.inject(handler, request, {})

        assert kwargs["page"] == 5

    @pytest.mark.asyncio
    async def test_inject_body_param(self, injector: ParameterInjector) -> None:
        """Body params should be injected."""

        async def handler(user: CreateUserSchema = Body()) -> dict:
            return {"name": user.name}

        request = create_request(method="POST", body=b'{"name": "Alice"}')
        kwargs = await injector.inject(handler, request, {})

        assert isinstance(kwargs["user"], CreateUserSchema)
        assert kwargs["user"].name == "Alice"

    @pytest.mark.asyncio
    async def test_inject_convention_path_param(
        self, injector: ParameterInjector
    ) -> None:
        """Path params without Path() marker should work by convention."""

        async def handler(id: int) -> dict:
            return {"id": id}

        request = create_request()
        kwargs = await injector.inject(handler, request, {"id": "123"})

        assert kwargs["id"] == 123

    @pytest.mark.asyncio
    async def test_inject_convention_query_param(
        self, injector: ParameterInjector
    ) -> None:
        """Query params without Query() marker should work by convention."""

        async def handler(search: str) -> dict:
            return {"search": search}

        request = create_request(query_string="search=hello")
        kwargs = await injector.inject(handler, request, {})

        assert kwargs["search"] == "hello"

    @pytest.mark.asyncio
    async def test_inject_param_with_default(self, injector: ParameterInjector) -> None:
        """Params with Python defaults should use them when not provided."""

        async def handler(page: int = 1) -> dict:
            return {"page": page}

        request = create_request()
        kwargs = await injector.inject(handler, request, {})

        assert kwargs["page"] == 1

    @pytest.mark.asyncio
    async def test_inject_missing_required_raises(
        self, injector: ParameterInjector
    ) -> None:
        """Missing required params should raise ValidationError."""

        async def handler(required_param: str) -> dict:
            return {"value": required_param}

        request = create_request()

        with pytest.raises(ValidationError) as exc_info:
            await injector.inject(handler, request, {})

        assert "required_param" in exc_info.value.errors[0].msg

    @pytest.mark.asyncio
    async def test_inject_combined_params(self, injector: ParameterInjector) -> None:
        """Multiple param sources should work together."""

        async def handler(
            request: Request,
            org_id: int = Path(),
            user: CreateUserSchema = Body(),
            limit: int = Query(default=10),
        ) -> dict:
            return {
                "org_id": org_id,
                "name": user.name,
                "limit": limit,
            }

        request_obj = create_request(
            method="POST",
            query_string="limit=20",
            body=b'{"name": "Alice"}',
        )
        kwargs = await injector.inject(handler, request_obj, {"org_id": "5"})

        assert kwargs["request"] is request_obj
        assert kwargs["org_id"] == 5
        assert kwargs["user"].name == "Alice"
        assert kwargs["limit"] == 20
