"""CRUD code generator."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pykour.generators.field_inference import FieldInferrer
from pykour.generators.naming import pluralize, singularize, snake_to_pascal
from pykour.generators.templates import (
    COLLECTION_ROUTE_TEMPLATE,
    ITEM_ROUTE_TEMPLATE,
    SCHEMA_TEMPLATE,
    TEST_TEMPLATE,
)

if TYPE_CHECKING:
    from pykour.db.migrations.table import Table

logger = logging.getLogger("pykour")


def _write_file(file_path: Path, content: str) -> None:
    """Write content to file with error handling.

    Args:
        file_path: Path to the file to write.
        content: Content to write.

    Raises:
        RuntimeError: If writing fails due to OS error.
    """
    try:
        file_path.write_text(content)
    except OSError as e:
        logger.error("Failed to write file %s: %s", file_path, e)
        raise RuntimeError(f"Failed to write file {file_path}: {e}") from e


class CRUDGenerator:
    """Generate CRUD route files for a resource."""

    def __init__(
        self,
        resource_name: str,
        *,
        table_name: str | None = None,
        table_class: type[Table] | None = None,
        id_field: str = "id",
        id_type: str = "int",
        routes_dir: str = "routes",
    ) -> None:
        """Initialize the CRUD generator.

        Args:
            resource_name: Resource name (e.g., "users", "products").
            table_name: Database table name. Defaults to resource_name.
            table_class: Table class for field inference.
            id_field: Primary key field name.
            id_type: Python type for the ID field.
            routes_dir: Base routes directory.
        """
        self.resource_name = resource_name.lower()
        # Always singularize first, then derive plural from singular
        # This handles both "user" and "users" inputs correctly
        self.resource_singular = singularize(self.resource_name)
        self.resource_plural = pluralize(self.resource_singular)
        self.resource_pascal = snake_to_pascal(self.resource_singular)
        self.resource_title = self.resource_pascal

        self.table_name = table_name or self.resource_plural
        self.table_class = table_class
        self.id_field = id_field
        self.id_type = id_type
        self.routes_dir = Path(routes_dir)

    def generate(
        self,
        *,
        with_schema: bool = False,
        with_tests: bool = False,
        force: bool = False,
    ) -> list[Path]:
        """Generate CRUD files.

        Args:
            with_schema: Generate schema file.
            with_tests: Generate test file.
            force: Overwrite existing files.

        Returns:
            List of created file paths.

        Raises:
            FileExistsError: If files exist and force is False.
        """
        created_files: list[Path] = []

        # Generate collection route (list + create)
        collection_path = self._generate_collection_route(with_schema, force)
        created_files.append(collection_path)

        # Generate item route (get, update, delete)
        item_path = self._generate_item_route(with_schema, force)
        created_files.append(item_path)

        # Generate schema file if requested
        if with_schema:
            schema_path = self._generate_schema(force)
            created_files.append(schema_path)

        # Generate test file if requested
        if with_tests:
            test_path = self._generate_test(force)
            created_files.append(test_path)

        return created_files

    def _generate_collection_route(
        self,
        with_schema: bool,
        force: bool,
    ) -> Path:
        """Generate the collection route file (list + create)."""
        route_dir = self.routes_dir / "api" / self.resource_plural
        route_dir.mkdir(parents=True, exist_ok=True)

        route_file = route_dir / "route.py"
        if route_file.exists() and not force:
            raise FileExistsError(f"File already exists: {route_file}")

        # Build schema import
        if with_schema:
            schema_import = f"\nfrom schemas.{self.resource_singular} import Create{self.resource_pascal}Schema\n"
            create_schema = f"Create{self.resource_pascal}Schema"
        else:
            schema_import = ""
            create_schema = "dict"

        content = COLLECTION_ROUTE_TEMPLATE.format(
            resource_title=self.resource_title,
            resource_plural=self.resource_plural,
            resource_singular=self.resource_singular,
            table_name=self.table_name,
            schema_import=schema_import,
            create_schema=create_schema,
        )

        _write_file(route_file, content)
        return route_file

    def _generate_item_route(
        self,
        with_schema: bool,
        force: bool,
    ) -> Path:
        """Generate the item route file (get, update, delete)."""
        route_dir = (
            self.routes_dir / "api" / self.resource_plural / f"[{self.id_field}]"
        )
        route_dir.mkdir(parents=True, exist_ok=True)

        route_file = route_dir / "route.py"
        if route_file.exists() and not force:
            raise FileExistsError(f"File already exists: {route_file}")

        # Build schema import
        if with_schema:
            schema_import = f"\nfrom schemas.{self.resource_singular} import Update{self.resource_pascal}Schema\n"
            update_schema = f"Update{self.resource_pascal}Schema"
        else:
            schema_import = ""
            update_schema = "dict"

        content = ITEM_ROUTE_TEMPLATE.format(
            resource_title=self.resource_title,
            resource_plural=self.resource_plural,
            resource_singular=self.resource_singular,
            table_name=self.table_name,
            id_field=self.id_field,
            id_type=self.id_type,
            schema_import=schema_import,
            update_schema=update_schema,
        )

        _write_file(route_file, content)
        return route_file

    def _generate_schema(self, force: bool) -> Path:
        """Generate the schema file."""
        schema_dir = Path("schemas")
        schema_dir.mkdir(parents=True, exist_ok=True)

        schema_file = schema_dir / f"{self.resource_singular}.py"
        if schema_file.exists() and not force:
            raise FileExistsError(f"File already exists: {schema_file}")

        # Generate field definitions
        if self.table_class is not None:
            # Infer fields from Table definition
            inferrer = FieldInferrer()
            fields = inferrer.infer_from_table(self.table_class)
            create_fields = inferrer.generate_create_fields(fields)
            update_fields = inferrer.generate_update_fields(fields)
        else:
            # Placeholder for manual customization
            create_fields = "    # TODO: Add fields for create operation\n    pass"
            update_fields = "    # TODO: Add fields for update operation\n    pass"

        content = SCHEMA_TEMPLATE.format(
            resource_title=self.resource_title,
            resource_pascal=self.resource_pascal,
            create_fields=create_fields,
            update_fields=update_fields,
        )

        _write_file(schema_file, content)
        return schema_file

    def _generate_test(self, force: bool) -> Path:
        """Generate the test file."""
        test_dir = Path("tests")
        test_dir.mkdir(parents=True, exist_ok=True)

        test_file = test_dir / f"test_{self.resource_plural}_api.py"
        if test_file.exists() and not force:
            raise FileExistsError(f"File already exists: {test_file}")

        content = TEST_TEMPLATE.format(
            resource_title=self.resource_title,
            resource_pascal=self.resource_pascal,
            resource_plural=self.resource_plural,
            resource_singular=self.resource_singular,
        )

        _write_file(test_file, content)
        return test_file
