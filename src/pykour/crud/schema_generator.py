"""Generate Schema classes from Table definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pykour.db.migrations.types import (
    BigInt,
    Boolean,
    Date,
    DateTime,
    Decimal,
    Float,
    Integer,
    JSON,
    SmallInt,
    String,
    Text,
    Time,
    UUID,
)
from pykour.schema.base import Schema
from pykour.schema.fields import MISSING, FieldInfo

if TYPE_CHECKING:
    from pykour.db.migrations.table import Column, Table


# Mapping from Column type to Python type
COLUMN_TYPE_MAP: dict[type, type] = {
    Integer: int,
    SmallInt: int,
    BigInt: int,
    String: str,
    Text: str,
    Boolean: bool,
    Float: float,
    Decimal: float,
    DateTime: str,
    Date: str,
    Time: str,
    JSON: dict,
    UUID: str,
}


def column_to_python_type(column: Column) -> type:
    """Map Column type to Python type."""
    col_type = type(column.type)
    return COLUMN_TYPE_MAP.get(col_type, str)


def column_to_field_info(column: Column) -> FieldInfo:
    """Extract validation constraints from Column.

    Maps Column attributes to FieldInfo:
    - nullable=False -> required field (no default)
    - nullable=True -> default=None
    - String(length) -> max_length=length
    - default=X -> default=X
    """
    kwargs: dict[str, Any] = {}

    # Handle default value
    if column.default is not None:
        # Skip SQL function defaults like CURRENT_TIMESTAMP
        if isinstance(column.default, str) and column.default.upper() in (
            "CURRENT_TIMESTAMP",
            "NOW()",
        ):
            # Don't set default for SQL function defaults
            pass
        else:
            kwargs["default"] = column.default
    elif column.nullable:
        kwargs["default"] = None

    # Handle String length constraint
    if isinstance(column.type, String):
        kwargs["max_length"] = column.type.length

    return FieldInfo(**kwargs) if kwargs else FieldInfo()


def generate_schema_class(
    name: str,
    table: type[Table],
    exclude_fields: list[str] | None = None,
    readonly_fields: list[str] | None = None,
    for_create: bool = True,
) -> type[Schema]:
    """Dynamically create a Schema class from Table definition.

    Args:
        name: Name for the generated schema class.
        table: Table class to generate schema from.
        exclude_fields: Fields to exclude from the schema.
        readonly_fields: Fields that cannot be set (excluded from create/update).
        for_create: True for create schema, False for update schema.

    Returns:
        A dynamically generated Schema subclass.
    """
    exclude = exclude_fields or []
    readonly = readonly_fields or []
    columns = table.get_columns()

    annotations: dict[str, Any] = {}
    namespace: dict[str, Any] = {"__module__": "pykour.crud.generated"}

    for col_name, column in columns.items():
        # Skip excluded fields
        if col_name in exclude:
            continue

        # Skip readonly fields
        if col_name in readonly:
            continue

        # Skip autoincrement primary key for create
        if column.primary_key and column.autoincrement and for_create:
            continue

        python_type: Any = column_to_python_type(column)
        field_info = column_to_field_info(column)

        # Make nullable types Optional
        if column.nullable or field_info.default is not MISSING:
            if field_info.default is None:
                python_type = python_type | None

        annotations[col_name] = python_type

        # Only add field info if it has meaningful metadata
        if (
            field_info.has_default
            or field_info.max_length is not None
            or field_info.min_length is not None
        ):
            namespace[col_name] = field_info

    namespace["__annotations__"] = annotations

    # Create class dynamically
    return cast(type[Schema], type(name, (Schema,), namespace))


class TableSchemaGenerator:
    """Generate Schema classes for CRUD operations from a Table."""

    def __init__(
        self,
        table: type[Table],
        exclude_fields: list[str] | None = None,
        readonly_fields: list[str] | None = None,
    ) -> None:
        """Initialize the generator.

        Args:
            table: Table class to generate schemas from.
            exclude_fields: Fields to exclude from all schemas.
            readonly_fields: Fields that cannot be set on create/update.
        """
        self._table = table
        self._exclude = exclude_fields or []
        self._readonly = readonly_fields or []
        self._create_schema: type[Schema] | None = None
        self._update_schema: type[Schema] | None = None

    @property
    def create_schema(self) -> type[Schema]:
        """Get or create the schema for create operations."""
        if self._create_schema is None:
            self._create_schema = generate_schema_class(
                f"{self._table.__name__}Create",
                self._table,
                self._exclude,
                self._readonly,
                for_create=True,
            )
        return self._create_schema

    @property
    def update_schema(self) -> type[Schema]:
        """Get or create the schema for update operations."""
        if self._update_schema is None:
            self._update_schema = generate_schema_class(
                f"{self._table.__name__}Update",
                self._table,
                self._exclude,
                self._readonly,
                for_create=False,
            )
        return self._update_schema
