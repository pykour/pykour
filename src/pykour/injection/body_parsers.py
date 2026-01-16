"""Body parameter parsing strategies for Pykour."""

from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from typing import Any, cast

from pykour.schema import Schema
from pykour.schema.errors import ErrorDetail, ValidationError


class BodyParser(ABC):
    """Abstract base class for body parameter parsing strategies.

    Each parser handles a specific type of body parameter (Schema, dict, dataclass, etc.)
    """

    @abstractmethod
    def can_parse(self, param_type: type) -> bool:
        """Check if this parser can handle the given parameter type.

        Args:
            param_type: The type of the parameter.

        Returns:
            True if this parser can handle the type.
        """
        ...

    @abstractmethod
    def parse(self, param_name: str, param_type: type, body_data: Any) -> Any:
        """Parse body data into the target type.

        Args:
            param_name: Name of the parameter (for error messages).
            param_type: Target type to parse into.
            body_data: Raw body data (usually dict from JSON).

        Returns:
            Parsed value of the target type.

        Raises:
            ValidationError: If parsing fails.
        """
        ...


class SchemaBodyParser(BodyParser):
    """Parser for pykour Schema subclasses."""

    def can_parse(self, param_type: type) -> bool:
        """Check if param_type is a Schema subclass."""
        return isinstance(param_type, type) and issubclass(param_type, Schema)

    def parse(self, param_name: str, param_type: type, body_data: Any) -> Any:
        """Parse body_data into a Schema instance."""
        try:
            return param_type(**body_data)
        except ValidationError:
            raise
        except (TypeError, ValueError) as e:
            raise ValidationError(
                [
                    ErrorDetail(
                        loc=("body", param_name),
                        msg=str(e),
                        type="value_error.schema",
                    )
                ]
            ) from e


class DictBodyParser(BodyParser):
    """Parser for dict type parameters."""

    def can_parse(self, param_type: type) -> bool:
        """Check if param_type is dict."""
        return param_type is dict

    def parse(self, param_name: str, param_type: type, body_data: Any) -> Any:
        """Return body_data as-is for dict type."""
        return body_data


class DataclassBodyParser(BodyParser):
    """Parser for dataclass types."""

    def can_parse(self, param_type: type) -> bool:
        """Check if param_type is a dataclass."""
        return dataclasses.is_dataclass(param_type) and isinstance(param_type, type)

    def parse(self, param_name: str, param_type: type, body_data: Any) -> Any:
        """Parse body_data into a dataclass instance."""
        try:
            return param_type(**body_data)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                [
                    ErrorDetail(
                        loc=("body", param_name),
                        msg=str(e),
                        type="value_error.dataclass",
                    )
                ]
            ) from e


class PydanticV2BodyParser(BodyParser):
    """Parser for Pydantic v2 models."""

    def can_parse(self, param_type: type) -> bool:
        """Check if param_type is a Pydantic v2 model."""
        return isinstance(param_type, type) and hasattr(param_type, "model_validate")

    def parse(self, param_name: str, param_type: type, body_data: Any) -> Any:
        """Parse body_data into a Pydantic v2 model instance."""
        try:
            # Cast to Any since model_validate is a pydantic-specific method
            pydantic_type = cast(Any, param_type)
            return pydantic_type.model_validate(body_data)
        except Exception as e:
            raise ValidationError(
                [
                    ErrorDetail(
                        loc=("body", param_name),
                        msg=str(e),
                        type="value_error.pydantic",
                    )
                ]
            ) from e


class PydanticV1BodyParser(BodyParser):
    """Parser for Pydantic v1 models."""

    def can_parse(self, param_type: type) -> bool:
        """Check if param_type is a Pydantic v1 model."""
        return isinstance(param_type, type) and hasattr(param_type, "parse_obj")

    def parse(self, param_name: str, param_type: type, body_data: Any) -> Any:
        """Parse body_data into a Pydantic v1 model instance."""
        try:
            # Cast to Any since parse_obj is a pydantic-specific method
            pydantic_type = cast(Any, param_type)
            return pydantic_type.parse_obj(body_data)
        except Exception as e:
            raise ValidationError(
                [
                    ErrorDetail(
                        loc=("body", param_name),
                        msg=str(e),
                        type="value_error.pydantic",
                    )
                ]
            ) from e


class PrimitiveBodyParser(BodyParser):
    """Parser for primitive types (int, float, str, bool)."""

    _PRIMITIVE_TYPES = (int, float, str, bool)

    def can_parse(self, param_type: type) -> bool:
        """Check if param_type is a primitive type."""
        return param_type in self._PRIMITIVE_TYPES

    def parse(self, param_name: str, param_type: type, body_data: Any) -> Any:
        """Parse body_data into a primitive type."""
        if isinstance(body_data, param_type):
            return body_data
        try:
            return param_type(body_data)
        except (TypeError, ValueError) as e:
            raise ValidationError(
                [
                    ErrorDetail(
                        loc=("body", param_name),
                        msg=f"Cannot coerce body to {param_type.__name__}: {e}",
                        type="type_error",
                    )
                ]
            ) from e


class ListBodyParser(BodyParser):
    """Parser for list type parameters."""

    def can_parse(self, param_type: type) -> bool:
        """Check if param_type is list."""
        return param_type is list

    def parse(self, param_name: str, param_type: type, body_data: Any) -> Any:
        """Validate body_data is a list."""
        if isinstance(body_data, list):
            return body_data
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("body", param_name),
                    msg=f"Expected list, got {type(body_data).__name__}",
                    type="type_error",
                )
            ]
        )


# Default parsers in priority order
# Note: Order matters! Schema must come before DataclassBodyParser since
# Schema might satisfy dataclass check. PydanticV2 must come before PydanticV1.
DEFAULT_BODY_PARSERS: list[BodyParser] = [
    SchemaBodyParser(),
    DictBodyParser(),
    DataclassBodyParser(),
    PydanticV2BodyParser(),
    PydanticV1BodyParser(),
    PrimitiveBodyParser(),
    ListBodyParser(),
]
