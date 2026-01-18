"""Tests for body parameter parsing strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from pykour.injection.body_parsers import (
    DEFAULT_BODY_PARSERS,
    DataclassBodyParser,
    DictBodyParser,
    ListBodyParser,
    PrimitiveBodyParser,
    PydanticV1BodyParser,
    PydanticV2BodyParser,
    SchemaBodyParser,
)
from pykour.schema import Schema
from pykour.schema.errors import ValidationError


class TestSchemaBodyParser:
    """Tests for SchemaBodyParser."""

    def test_can_parse_schema_subclass(self) -> None:
        """Schema subclasses should be recognizable."""

        class MySchema(Schema):
            name: str

        parser = SchemaBodyParser()
        assert parser.can_parse(MySchema) is True

    def test_cannot_parse_non_schema(self) -> None:
        """Non-Schema types should not be recognizable."""
        parser = SchemaBodyParser()
        assert parser.can_parse(dict) is False
        assert parser.can_parse(str) is False
        assert parser.can_parse(int) is False

    def test_parse_valid_schema(self) -> None:
        """Valid data should parse to Schema instance."""

        class UserSchema(Schema):
            name: str
            age: int

        parser = SchemaBodyParser()
        result = parser.parse("user", UserSchema, {"name": "Alice", "age": 30})

        assert isinstance(result, UserSchema)
        assert result.name == "Alice"
        assert result.age == 30

    def test_parse_invalid_raises_validation_error(self) -> None:
        """Invalid data should raise ValidationError."""

        class UserSchema(Schema):
            name: str
            age: int

        parser = SchemaBodyParser()
        with pytest.raises(ValidationError):
            parser.parse("user", UserSchema, {"name": "Alice"})  # Missing age


class TestDictBodyParser:
    """Tests for DictBodyParser."""

    def test_can_parse_dict(self) -> None:
        """dict type should be recognizable."""
        parser = DictBodyParser()
        assert parser.can_parse(dict) is True

    def test_cannot_parse_non_dict(self) -> None:
        """Non-dict types should not be recognizable."""
        parser = DictBodyParser()
        assert parser.can_parse(list) is False
        assert parser.can_parse(str) is False

    def test_parse_returns_dict(self) -> None:
        """Should return body_data as-is for dict type."""
        parser = DictBodyParser()
        data = {"key": "value", "number": 42}

        result = parser.parse("data", dict, data)

        assert result is data
        assert result == {"key": "value", "number": 42}


class TestDataclassBodyParser:
    """Tests for DataclassBodyParser."""

    def test_can_parse_dataclass(self) -> None:
        """Dataclass types should be recognizable."""

        @dataclass
        class User:
            name: str
            age: int

        parser = DataclassBodyParser()
        assert parser.can_parse(User) is True

    def test_cannot_parse_non_dataclass(self) -> None:
        """Non-dataclass types should not be recognizable."""
        parser = DataclassBodyParser()
        assert parser.can_parse(dict) is False
        assert parser.can_parse(str) is False

    def test_cannot_parse_schema(self) -> None:
        """Schema (even if dataclass-like) should be checked differently."""

        class MySchema(Schema):
            name: str

        parser = DataclassBodyParser()
        # Schema is not a dataclass
        assert parser.can_parse(MySchema) is False

    def test_parse_valid_dataclass(self) -> None:
        """Valid data should parse to dataclass instance."""

        @dataclass
        class User:
            name: str
            age: int

        parser = DataclassBodyParser()
        result = parser.parse("user", User, {"name": "Bob", "age": 25})

        assert isinstance(result, User)
        assert result.name == "Bob"
        assert result.age == 25

    def test_parse_invalid_raises_validation_error(self) -> None:
        """Invalid data should raise ValidationError."""

        @dataclass
        class User:
            name: str
            age: int

        parser = DataclassBodyParser()
        with pytest.raises(ValidationError):
            # Missing required field
            parser.parse("user", User, {"name": "Bob"})


class TestPydanticV2BodyParser:
    """Tests for PydanticV2BodyParser."""

    def test_can_parse_with_model_validate(self) -> None:
        """Types with model_validate should be recognizable."""

        class FakePydanticV2:
            @classmethod
            def model_validate(cls, data: Any) -> "FakePydanticV2":
                return cls()

        parser = PydanticV2BodyParser()
        assert parser.can_parse(FakePydanticV2) is True

    def test_cannot_parse_without_model_validate(self) -> None:
        """Types without model_validate should not be recognizable."""
        parser = PydanticV2BodyParser()
        assert parser.can_parse(dict) is False
        assert parser.can_parse(str) is False

    def test_parse_calls_model_validate(self) -> None:
        """Should call model_validate for parsing."""

        class FakePydanticV2:
            def __init__(self, name: str = "") -> None:
                self.name = name

            @classmethod
            def model_validate(cls, data: dict) -> "FakePydanticV2":
                return cls(name=data.get("name", ""))

        parser = PydanticV2BodyParser()
        result = parser.parse("model", FakePydanticV2, {"name": "Alice"})

        assert isinstance(result, FakePydanticV2)
        assert result.name == "Alice"

    def test_parse_error_raises_validation_error(self) -> None:
        """Errors during model_validate should raise ValidationError."""

        class FailingPydanticV2:
            @classmethod
            def model_validate(cls, data: Any) -> "FailingPydanticV2":
                raise ValueError("Invalid data")

        parser = PydanticV2BodyParser()
        with pytest.raises(ValidationError):
            parser.parse("model", FailingPydanticV2, {"name": "test"})


class TestPydanticV1BodyParser:
    """Tests for PydanticV1BodyParser."""

    def test_can_parse_with_parse_obj(self) -> None:
        """Types with parse_obj should be recognizable."""

        class FakePydanticV1:
            @classmethod
            def parse_obj(cls, data: Any) -> "FakePydanticV1":
                return cls()

        parser = PydanticV1BodyParser()
        assert parser.can_parse(FakePydanticV1) is True

    def test_cannot_parse_without_parse_obj(self) -> None:
        """Types without parse_obj should not be recognizable."""
        parser = PydanticV1BodyParser()
        assert parser.can_parse(dict) is False

    def test_cannot_parse_pydantic_v2(self) -> None:
        """Pydantic v2 (with model_validate) should be handled by V2 parser."""

        class FakePydanticV2:
            @classmethod
            def model_validate(cls, data: Any) -> "FakePydanticV2":
                return cls()

        parser = PydanticV1BodyParser()
        # Has model_validate but no parse_obj
        assert parser.can_parse(FakePydanticV2) is False

    def test_parse_calls_parse_obj(self) -> None:
        """Should call parse_obj for parsing."""

        class FakePydanticV1:
            def __init__(self, name: str = "") -> None:
                self.name = name

            @classmethod
            def parse_obj(cls, data: dict) -> "FakePydanticV1":
                return cls(name=data.get("name", ""))

        parser = PydanticV1BodyParser()
        result = parser.parse("model", FakePydanticV1, {"name": "Bob"})

        assert isinstance(result, FakePydanticV1)
        assert result.name == "Bob"

    def test_parse_error_raises_validation_error(self) -> None:
        """Errors during parse_obj should raise ValidationError."""

        class FailingPydanticV1:
            @classmethod
            def parse_obj(cls, data: Any) -> "FailingPydanticV1":
                raise ValueError("Invalid data")

        parser = PydanticV1BodyParser()
        with pytest.raises(ValidationError):
            parser.parse("model", FailingPydanticV1, {"name": "test"})


class TestPrimitiveBodyParser:
    """Tests for PrimitiveBodyParser."""

    def test_can_parse_int(self) -> None:
        """int type should be recognizable."""
        parser = PrimitiveBodyParser()
        assert parser.can_parse(int) is True

    def test_can_parse_str(self) -> None:
        """str type should be recognizable."""
        parser = PrimitiveBodyParser()
        assert parser.can_parse(str) is True

    def test_can_parse_float(self) -> None:
        """float type should be recognizable."""
        parser = PrimitiveBodyParser()
        assert parser.can_parse(float) is True

    def test_can_parse_bool(self) -> None:
        """bool type should be recognizable."""
        parser = PrimitiveBodyParser()
        assert parser.can_parse(bool) is True

    def test_cannot_parse_complex_types(self) -> None:
        """Complex types should not be recognizable."""
        parser = PrimitiveBodyParser()
        assert parser.can_parse(dict) is False
        assert parser.can_parse(list) is False

    def test_parse_already_correct_type(self) -> None:
        """Value already of correct type should be returned as-is."""
        parser = PrimitiveBodyParser()

        result = parser.parse("value", int, 42)
        assert result == 42

        result = parser.parse("value", str, "hello")
        assert result == "hello"

    def test_parse_coerces_type(self) -> None:
        """Should coerce value to target type."""
        parser = PrimitiveBodyParser()

        result = parser.parse("value", int, "42")
        assert result == 42
        assert isinstance(result, int)

        result = parser.parse("value", float, "3.14")
        assert result == 3.14
        assert isinstance(result, float)

        result = parser.parse("value", str, 123)
        assert result == "123"
        assert isinstance(result, str)

    def test_parse_invalid_raises_validation_error(self) -> None:
        """Invalid coercion should raise ValidationError."""
        parser = PrimitiveBodyParser()

        with pytest.raises(ValidationError):
            parser.parse("value", int, "not_a_number")


class TestListBodyParser:
    """Tests for ListBodyParser."""

    def test_can_parse_list(self) -> None:
        """list type should be recognizable."""
        parser = ListBodyParser()
        assert parser.can_parse(list) is True

    def test_cannot_parse_non_list(self) -> None:
        """Non-list types should not be recognizable."""
        parser = ListBodyParser()
        assert parser.can_parse(dict) is False
        assert parser.can_parse(tuple) is False

    def test_parse_returns_list(self) -> None:
        """Should return body_data if it's a list."""
        parser = ListBodyParser()
        data = [1, 2, 3, "four"]

        result = parser.parse("items", list, data)

        assert result is data
        assert result == [1, 2, 3, "four"]

    def test_parse_non_list_raises_validation_error(self) -> None:
        """Non-list data should raise ValidationError."""
        parser = ListBodyParser()

        with pytest.raises(ValidationError):
            parser.parse("items", list, {"not": "a list"})


class TestDefaultBodyParsersOrder:
    """Tests for DEFAULT_BODY_PARSERS priority order."""

    def test_schema_before_dataclass(self) -> None:
        """Schema parser should come before dataclass parser."""
        schema_idx = None
        dataclass_idx = None

        for idx, parser in enumerate(DEFAULT_BODY_PARSERS):
            if isinstance(parser, SchemaBodyParser):
                schema_idx = idx
            elif isinstance(parser, DataclassBodyParser):
                dataclass_idx = idx

        assert schema_idx is not None
        assert dataclass_idx is not None
        assert schema_idx < dataclass_idx

    def test_pydantic_v2_before_v1(self) -> None:
        """Pydantic v2 parser should come before v1."""
        v2_idx = None
        v1_idx = None

        for idx, parser in enumerate(DEFAULT_BODY_PARSERS):
            if isinstance(parser, PydanticV2BodyParser):
                v2_idx = idx
            elif isinstance(parser, PydanticV1BodyParser):
                v1_idx = idx

        assert v2_idx is not None
        assert v1_idx is not None
        assert v2_idx < v1_idx

    def test_parser_selection_order(self) -> None:
        """First matching parser should be used."""

        class MySchema(Schema):
            name: str

        # Find the first parser that can handle MySchema
        selected_parser = None
        for parser in DEFAULT_BODY_PARSERS:
            if parser.can_parse(MySchema):
                selected_parser = parser
                break

        assert isinstance(selected_parser, SchemaBodyParser)

    def test_default_parsers_count(self) -> None:
        """Should have expected number of default parsers."""
        assert len(DEFAULT_BODY_PARSERS) == 7

    def test_default_parsers_types(self) -> None:
        """Should include all expected parser types."""
        parser_types = [type(p) for p in DEFAULT_BODY_PARSERS]

        assert SchemaBodyParser in parser_types
        assert DictBodyParser in parser_types
        assert DataclassBodyParser in parser_types
        assert PydanticV2BodyParser in parser_types
        assert PydanticV1BodyParser in parser_types
        assert PrimitiveBodyParser in parser_types
        assert ListBodyParser in parser_types
