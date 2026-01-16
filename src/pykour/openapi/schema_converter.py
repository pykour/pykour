"""Convert Pykour Schema to JSON Schema."""

from datetime import date, datetime
from typing import Any, Union, get_args, get_origin
from uuid import UUID

from pykour.schema.fields import FieldInfo


# Python type to JSON Schema type mapping
TYPE_MAPPING: dict[type, dict[str, str]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    bytes: {"type": "string", "format": "binary"},
    UUID: {"type": "string", "format": "uuid"},
    datetime: {"type": "string", "format": "date-time"},
    date: {"type": "string", "format": "date"},
}


class SchemaConverter:
    """Convert Pykour Schema classes to JSON Schema format."""

    def __init__(self) -> None:
        self._definitions: dict[str, dict[str, Any]] = {}

    def convert(self, schema_class: type) -> dict[str, Any]:
        """Convert a Schema class to JSON Schema.

        Args:
            schema_class: A Pykour Schema subclass.

        Returns:
            JSON Schema dictionary.
        """
        # Import here to avoid circular import
        from pykour.schema.base import Schema

        if not isinstance(schema_class, type) or not issubclass(schema_class, Schema):
            raise TypeError(f"Expected Schema subclass, got {schema_class}")

        return self._convert_schema_class(schema_class)

    def _convert_schema_class(self, schema_class: type) -> dict[str, Any]:
        """Convert a Schema class to JSON Schema object."""
        schema_fields = getattr(schema_class, "__schema_fields__", {})
        properties: dict[str, Any] = {}
        required: list[str] = []

        for field_name, (field_type, field_info) in schema_fields.items():
            prop = self._convert_type(field_type, field_info)

            # Apply field info constraints
            prop = self._apply_constraints(prop, field_info)

            properties[field_name] = prop

            # Check if field is required
            if not field_info.has_default:
                required.append(field_name)

        result: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }

        if required:
            result["required"] = required

        # Add title from class name
        result["title"] = schema_class.__name__

        return result

    def _convert_type(
        self, py_type: type, field_info: FieldInfo | None = None
    ) -> dict[str, Any]:
        """Convert a Python type to JSON Schema type."""
        # Import here to avoid circular import
        from pykour.schema.base import Schema

        origin = get_origin(py_type)
        args = get_args(py_type)

        # Handle Optional[T] (Union[T, None])
        if origin is Union:
            non_none_types = [t for t in args if t is not type(None)]

            if len(non_none_types) == 1:
                # Simple Optional[T]
                inner_schema = self._convert_type(non_none_types[0], field_info)
                # OpenAPI 3.1 uses "type": ["string", "null"] for nullable
                if "type" in inner_schema:
                    inner_schema["type"] = [inner_schema["type"], "null"]
                else:
                    # For complex types, use anyOf
                    return {"anyOf": [inner_schema, {"type": "null"}]}
                return inner_schema
            else:
                # Union of multiple types
                return {"anyOf": [self._convert_type(t) for t in non_none_types]}

        # Handle list[T]
        if origin is list:
            items_type = args[0] if args else Any
            return {"type": "array", "items": self._convert_type(items_type)}

        # Handle dict[K, V]
        if origin is dict:
            if args and len(args) == 2:
                val_type = args[1]
                return {
                    "type": "object",
                    "additionalProperties": self._convert_type(val_type),
                }
            return {"type": "object"}

        # Handle tuple
        if origin is tuple:
            if args:
                return {
                    "type": "array",
                    "items": [self._convert_type(t) for t in args],
                    "minItems": len(args),
                    "maxItems": len(args),
                }
            return {"type": "array"}

        # Handle nested Schema
        if isinstance(py_type, type) and issubclass(py_type, Schema):
            schema_name = py_type.__name__
            if schema_name not in self._definitions:
                self._definitions[schema_name] = self._convert_schema_class(py_type)
            return {"$ref": f"#/components/schemas/{schema_name}"}

        # Handle primitive types
        if py_type in TYPE_MAPPING:
            return TYPE_MAPPING[py_type].copy()

        # Handle Any
        if py_type is Any:
            return {}

        # Default to string
        return {"type": "string"}

    def _apply_constraints(
        self, schema: dict[str, Any], field_info: FieldInfo
    ) -> dict[str, Any]:
        """Apply FieldInfo constraints to JSON Schema."""
        # Numeric constraints
        if field_info.ge is not None:
            schema["minimum"] = field_info.ge
        if field_info.gt is not None:
            schema["exclusiveMinimum"] = field_info.gt
        if field_info.le is not None:
            schema["maximum"] = field_info.le
        if field_info.lt is not None:
            schema["exclusiveMaximum"] = field_info.lt

        # String/array length constraints
        if field_info.min_length is not None:
            schema["minLength"] = field_info.min_length
        if field_info.max_length is not None:
            schema["maxLength"] = field_info.max_length

        # Pattern constraint
        if field_info.pattern is not None:
            schema["pattern"] = field_info.pattern

        # Description
        if field_info.description is not None:
            schema["description"] = field_info.description

        # Default value
        if field_info.has_default and field_info.default_factory is None:
            default = field_info.default
            # Only include serializable defaults
            if isinstance(default, (str, int, float, bool, list, dict, type(None))):
                schema["default"] = default

        return schema

    def get_definitions(self) -> dict[str, dict[str, Any]]:
        """Get all collected schema definitions.

        Returns:
            Dictionary of schema name to JSON Schema.
        """
        return self._definitions.copy()


def python_type_to_json_schema(py_type: type) -> dict[str, Any]:
    """Convert a Python type to JSON Schema.

    Args:
        py_type: Python type to convert.

    Returns:
        JSON Schema dictionary.
    """
    converter = SchemaConverter()
    return converter._convert_type(py_type)
