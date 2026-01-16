"""CRUD route registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pykour.crud.config import ListConfig
from pykour.crud.handlers import (
    RouteHandler,
    create_create_handler,
    create_delete_handler,
    create_get_handler,
    create_list_handler,
    create_update_handler,
)
from pykour.crud.schema_generator import TableSchemaGenerator

if TYPE_CHECKING:
    from pykour.application import Pykour
    from pykour.db.migrations.table import Table


class CRUDRegistrar:
    """Handles CRUD route registration for a Pykour application."""

    def __init__(self, app: Pykour) -> None:
        """Initialize the registrar.

        Args:
            app: Pykour application instance.
        """
        self._app = app

    def register(
        self,
        path: str,
        table: type[Table],
        *,
        operations: list[str] | None = None,
        list_config: ListConfig | None = None,
        id_field: str | None = None,
        exclude_fields: list[str] | None = None,
        readonly_fields: list[str] | None = None,
    ) -> None:
        """Register CRUD endpoints for a Table.

        Args:
            path: Base path for the endpoints (e.g., "/api/users").
            table: Table class to generate CRUD for.
            operations: List of operations to enable.
                Options: "list", "get", "create", "update", "delete".
                Defaults to all operations.
            list_config: Configuration for list endpoint.
            id_field: Primary key field name. Auto-detected if not provided.
            exclude_fields: Fields to exclude from the API.
            readonly_fields: Fields that cannot be set on create/update.
        """
        ops = operations or ["list", "get", "create", "update", "delete"]
        list_cfg = list_config or ListConfig()
        exclude = exclude_fields or []
        readonly = readonly_fields or []

        # Auto-detect primary key field
        if id_field is None:
            id_field = self._detect_id_field(table)

        # Generate schemas
        schema_generator = TableSchemaGenerator(table, exclude, readonly)

        # Register collection routes (no id in path)
        collection_handlers: dict[str, RouteHandler] = {}
        if "list" in ops:
            collection_handlers["GET"] = create_list_handler(table, list_cfg)
        if "create" in ops:
            collection_handlers["POST"] = create_create_handler(
                table, schema_generator.create_schema, id_field
            )

        if collection_handlers:
            self._app.register_route(path, collection_handlers)

        # Register item routes (with id in path)
        item_path = f"{path}/[{id_field}]"
        item_handlers: dict[str, RouteHandler] = {}
        if "get" in ops:
            item_handlers["GET"] = create_get_handler(table, id_field)
        if "update" in ops:
            item_handlers["PUT"] = create_update_handler(
                table, schema_generator.update_schema, id_field
            )
        if "delete" in ops:
            item_handlers["DELETE"] = create_delete_handler(table, id_field)

        if item_handlers:
            self._app.register_route(item_path, item_handlers)

    def _detect_id_field(self, table: type[Table]) -> str:
        """Detect the primary key field from Table definition.

        Args:
            table: Table class.

        Returns:
            Name of the primary key field.

        Raises:
            ValueError: If no primary key is found.
        """
        for name, column in table.get_columns().items():
            if column.primary_key:
                return name
        raise ValueError(
            f"Table {table.__name__} has no primary key column. "
            "Please specify id_field explicitly."
        )
