"""Field inference for schema code generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

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

if TYPE_CHECKING:
    from pykour.db.migrations.table import Column, Table


# Mapping from Column type to Python type string for code generation
COLUMN_TYPE_TO_STR: dict[type, str] = {
    Integer: "int",
    SmallInt: "int",
    BigInt: "int",
    String: "str",
    Text: "str",
    Boolean: "bool",
    Float: "float",
    Decimal: "float",
    DateTime: "str",
    Date: "str",
    Time: "str",
    JSON: "dict",
    UUID: "str",
}

# Column names that are typically auto-generated
AUTO_GENERATED_COLUMNS: set[str] = {
    "id",
    "created_at",
    "created_on",
    "updated_at",
    "updated_on",
    "inserted_at",
}

# SQL function defaults that indicate auto-generation
AUTO_GENERATED_DEFAULTS: set[str] = {
    "current_timestamp",
    "now()",
    "uuid()",
    "gen_random_uuid()",
}


@dataclass
class InferredField:
    """Inferred field information from a database column."""

    name: str
    python_type: str
    nullable: bool
    default: Any
    max_length: int | None
    is_primary_key: bool
    is_auto_generated: bool


class FieldInferrer:
    """Infer schema fields from Table definition for code generation."""

    def __init__(self, exclude_auto_generated: bool = True) -> None:
        """Initialize the field inferrer.

        Args:
            exclude_auto_generated: Whether to exclude auto-generated columns
                from create schema.
        """
        self.exclude_auto_generated = exclude_auto_generated

    def infer_from_table(self, table: type[Table]) -> list[InferredField]:
        """Infer fields from a Table class definition.

        Args:
            table: Table class to infer fields from.

        Returns:
            List of inferred field information.
        """
        columns = table.get_columns()
        fields: list[InferredField] = []

        for col_name, column in columns.items():
            field = self._column_to_inferred_field(col_name, column)
            fields.append(field)

        return fields

    def _column_to_inferred_field(self, name: str, column: Column) -> InferredField:
        """Convert a Column to InferredField.

        Args:
            name: Column name.
            column: Column definition.

        Returns:
            InferredField with extracted information.
        """
        # Get Python type string
        col_type = type(column.type)
        python_type = COLUMN_TYPE_TO_STR.get(col_type, "str")

        # Get max_length for String types
        max_length = None
        if isinstance(column.type, String):
            max_length = column.type.length

        # Check if auto-generated
        is_auto_generated = self._is_auto_generated(name, column)

        return InferredField(
            name=name,
            python_type=python_type,
            nullable=column.nullable,
            default=column.default,
            max_length=max_length,
            is_primary_key=column.primary_key,
            is_auto_generated=is_auto_generated,
        )

    def _is_auto_generated(self, name: str, column: Column) -> bool:
        """Check if a column is auto-generated.

        Args:
            name: Column name.
            column: Column definition.

        Returns:
            True if the column is auto-generated.
        """
        # Autoincrement primary key
        if column.primary_key and column.autoincrement:
            return True

        # Known auto-generated column names
        if name.lower() in AUTO_GENERATED_COLUMNS:
            return True

        # SQL function defaults
        if column.default is not None and isinstance(column.default, str):
            if column.default.lower() in AUTO_GENERATED_DEFAULTS:
                return True

        return False

    def generate_create_fields(self, fields: list[InferredField]) -> str:
        """Generate field definitions for create schema.

        Auto-generated fields are excluded.

        Args:
            fields: List of inferred fields.

        Returns:
            Python code string for field definitions.
        """
        lines: list[str] = []

        for field in fields:
            # Skip auto-generated fields for create
            if self.exclude_auto_generated and field.is_auto_generated:
                continue

            line = self._generate_field_line(field, for_update=False)
            lines.append(line)

        if not lines:
            return "    pass"

        return "\n".join(lines)

    def generate_update_fields(self, fields: list[InferredField]) -> str:
        """Generate field definitions for update schema.

        All fields are Optional with default=None.
        Primary keys and auto-generated fields are excluded.

        Args:
            fields: List of inferred fields.

        Returns:
            Python code string for field definitions.
        """
        lines: list[str] = []

        for field in fields:
            # Skip primary keys for update
            if field.is_primary_key:
                continue

            # Skip auto-generated fields for update
            if self.exclude_auto_generated and field.is_auto_generated:
                continue

            line = self._generate_field_line(field, for_update=True)
            lines.append(line)

        if not lines:
            return "    pass"

        return "\n".join(lines)

    def _generate_field_line(self, field: InferredField, for_update: bool) -> str:
        """Generate a single field definition line.

        Args:
            field: Inferred field information.
            for_update: Whether this is for update schema (all Optional).

        Returns:
            Python code string for the field definition.
        """
        # Determine type annotation
        if for_update:
            type_annotation = f"{field.python_type} | None"
        elif field.nullable:
            type_annotation = f"{field.python_type} | None"
        else:
            type_annotation = field.python_type

        # Build Field() arguments
        field_args: list[str] = []

        # Add default for update schema
        if for_update:
            field_args.append("default=None")
        elif field.default is not None and not self._is_sql_function_default(
            field.default
        ):
            field_args.append(f"default={field.default!r}")
        elif field.nullable:
            field_args.append("default=None")

        # Add max_length for strings
        if field.max_length is not None:
            field_args.append(f"max_length={field.max_length}")

        # Generate the line
        if field_args:
            args_str = ", ".join(field_args)
            return f"    {field.name}: {type_annotation} = Field({args_str})"
        else:
            return f"    {field.name}: {type_annotation}"

    def _is_sql_function_default(self, default: Any) -> bool:
        """Check if a default value is a SQL function.

        Args:
            default: Default value to check.

        Returns:
            True if it's a SQL function default.
        """
        if not isinstance(default, str):
            return False
        return default.lower() in AUTO_GENERATED_DEFAULTS
