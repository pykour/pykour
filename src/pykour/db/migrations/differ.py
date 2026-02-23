"""Schema difference detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pykour.db.migrations.introspector import SchemaIntrospector
from pykour.db.migrations.table import Column, ColumnDef, IndexDef, Table

if TYPE_CHECKING:
    pass


@dataclass
class SchemaDiff:
    """Represents differences between Python schema and database."""

    tables_to_create: list[type[Table]] = field(default_factory=list)
    tables_to_drop: list[str] = field(default_factory=list)
    columns_to_add: list[tuple[str, str, Column]] = field(default_factory=list)
    columns_to_drop: list[tuple[str, str]] = field(default_factory=list)
    columns_to_alter: list[tuple[str, str, dict[str, Any]]] = field(
        default_factory=list
    )
    indexes_to_create: list[tuple[str, IndexDef]] = field(default_factory=list)
    indexes_to_drop: list[tuple[str, str]] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if there are no differences."""
        return (
            not self.tables_to_create
            and not self.tables_to_drop
            and not self.columns_to_add
            and not self.columns_to_drop
            and not self.columns_to_alter
            and not self.indexes_to_create
            and not self.indexes_to_drop
        )


class SchemaDiffer:
    """Compares Python table definitions with database schema."""

    def __init__(self, introspector: SchemaIntrospector) -> None:
        self._introspector = introspector

    async def diff(
        self,
        conn: Any,
        tables: list[type[Table]],
    ) -> SchemaDiff:
        """Compare Python table definitions with database.

        Args:
            conn: Database connection.
            tables: List of Table classes to compare.

        Returns:
            SchemaDiff with detected differences.
        """
        result = SchemaDiff()

        db_tables = set(await self._introspector.get_tables(conn))
        py_tables = {t.get_tablename(): t for t in tables}

        for name, table_cls in py_tables.items():
            if name not in db_tables:
                result.tables_to_create.append(table_cls)
            else:
                await self._diff_table(conn, name, table_cls, result)

        return result

    async def _diff_table(
        self,
        conn: Any,
        table_name: str,
        table_cls: type[Table],
        result: SchemaDiff,
    ) -> None:
        """Compare a single table with its database definition."""
        db_info = await self._introspector.get_table_info(conn, table_name)
        db_columns = {c.name: c for c in db_info.columns}
        py_columns = table_cls.get_columns()

        for col_name, col in py_columns.items():
            if col_name not in db_columns:
                result.columns_to_add.append((table_name, col_name, col))

        for col_name in db_columns:
            if col_name not in py_columns:
                result.columns_to_drop.append((table_name, col_name))

        self._diff_indexes(table_name, table_cls, db_info.indexes, result)

    def _diff_indexes(
        self,
        table_name: str,
        table_cls: type[Table],
        db_indexes: list,
        result: SchemaDiff,
    ) -> None:
        """Compare indexes between Python definition and database."""
        py_indexes = table_cls.get_indexes()

        db_index_names = {idx.name for idx in db_indexes}

        # Check for indexes to create
        for idx_def in py_indexes:
            if idx_def.name not in db_index_names:
                result.indexes_to_create.append((table_name, idx_def))

        # Collect Python index names
        py_index_names = {idx_def.name for idx_def in py_indexes}

        # Check for indexes to drop (only user-created indexes)
        for db_idx in db_indexes:
            # Skip SQLite auto-generated indexes
            if db_idx.name.startswith("sqlite_autoindex_"):
                continue
            # Only consider indexes we might have created (idx_ or uq_ prefix)
            if db_idx.name.startswith(("idx_", "uq_")):
                if db_idx.name not in py_index_names:
                    result.indexes_to_drop.append((table_name, db_idx.name))


def table_to_column_defs(table_cls: type[Table], driver: str) -> list[ColumnDef]:
    """Convert a Table class to ColumnDef list for operations."""
    columns = table_cls.get_columns()
    result = []

    for name, col in columns.items():
        result.append(
            ColumnDef(
                name=name,
                type_sql=col.type.to_sql(driver),
                primary_key=col.primary_key,
                nullable=col.nullable,
                unique=col.unique,
                default=col.default,
                autoincrement=col.autoincrement,
            )
        )

    return result


def column_to_column_def(name: str, col: Column, driver: str) -> ColumnDef:
    """Convert a Column to ColumnDef."""
    return ColumnDef(
        name=name,
        type_sql=col.type.to_sql(driver),
        primary_key=col.primary_key,
        nullable=col.nullable,
        unique=col.unique,
        default=col.default,
        autoincrement=col.autoincrement,
    )
