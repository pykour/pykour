"""Migration operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pykour.db.migrations.table import ColumnDef, IndexDef
from pykour.db.sql_utils import validate_identifier

if TYPE_CHECKING:
    from pykour.db.drivers.base import BaseDriver


class Operation(ABC):
    """Base class for migration operations."""

    @abstractmethod
    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        """Execute the operation."""

    @abstractmethod
    def reverse(self) -> Operation:
        """Return the reverse operation."""

    @abstractmethod
    def to_code(self) -> str:
        """Generate Python code for this operation."""


@dataclass
class CreateTable(Operation):
    """Create a new table."""

    name: str
    columns: list[ColumnDef]
    if_not_exists: bool = False

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        # Validate table and column names
        validate_identifier(self.name, "table")
        for col in self.columns:
            validate_identifier(col.name, "column")

        driver_name = driver.driver_name
        column_defs = ", ".join(col.to_sql(driver_name) for col in self.columns)
        exists_clause = "IF NOT EXISTS " if self.if_not_exists else ""
        sql = f"CREATE TABLE {exists_clause}{self.name} ({column_defs})"
        await conn.execute(sql)

    def reverse(self) -> Operation:
        return DropTable(self.name, _columns=self.columns)

    def to_code(self) -> str:
        columns_code = ",\n        ".join(
            self._column_to_code(col) for col in self.columns
        )
        return (
            f'op.create_table(\n        "{self.name}",\n        {columns_code},\n    )'
        )

    def _column_to_code(self, col: ColumnDef) -> str:
        parts = [f'"{col.name}"', f'"{col.type_sql}"']
        if col.primary_key:
            parts.append("primary_key=True")
        if col.autoincrement:
            parts.append("autoincrement=True")
        if not col.nullable and not col.primary_key:
            parts.append("nullable=False")
        if col.unique and not col.primary_key:
            parts.append("unique=True")
        if col.default is not None:
            if isinstance(col.default, str):
                parts.append(f'default="{col.default}"')
            else:
                parts.append(f"default={col.default}")
        return f"op.column({', '.join(parts)})"


@dataclass
class DropTable(Operation):
    """Drop a table."""

    name: str
    if_exists: bool = False
    _columns: list[ColumnDef] = field(default_factory=list)

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        validate_identifier(self.name, "table")
        exists_clause = "IF EXISTS " if self.if_exists else ""
        sql = f"DROP TABLE {exists_clause}{self.name}"
        await conn.execute(sql)

    def reverse(self) -> Operation:
        return CreateTable(self.name, self._columns)

    def to_code(self) -> str:
        return f'op.drop_table("{self.name}")'


@dataclass
class AddColumn(Operation):
    """Add a column to a table."""

    table: str
    column: ColumnDef

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        validate_identifier(self.table, "table")
        validate_identifier(self.column.name, "column")

        driver_name = driver.driver_name
        col_sql = self.column.to_sql(driver_name)
        sql = f"ALTER TABLE {self.table} ADD COLUMN {col_sql}"
        await conn.execute(sql)

    def reverse(self) -> Operation:
        return DropColumn(self.table, self.column.name, _column=self.column)

    def to_code(self) -> str:
        col = self.column
        parts = [f'"{col.name}"', f'"{col.type_sql}"']
        if col.primary_key:
            parts.append("primary_key=True")
        if col.autoincrement:
            parts.append("autoincrement=True")
        if not col.nullable:
            parts.append("nullable=False")
        if col.unique:
            parts.append("unique=True")
        if col.default is not None:
            if isinstance(col.default, str):
                parts.append(f'default="{col.default}"')
            else:
                parts.append(f"default={col.default}")
        return f'op.add_column("{self.table}", op.column({", ".join(parts)}))'


@dataclass
class DropColumn(Operation):
    """Drop a column from a table."""

    table: str
    column_name: str
    _column: ColumnDef | None = None

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        validate_identifier(self.table, "table")
        validate_identifier(self.column_name, "column")
        sql = f"ALTER TABLE {self.table} DROP COLUMN {self.column_name}"
        await conn.execute(sql)

    def reverse(self) -> Operation:
        if self._column is None:
            raise ValueError("Cannot reverse DropColumn without column definition")
        return AddColumn(self.table, self._column)

    def to_code(self) -> str:
        return f'op.drop_column("{self.table}", "{self.column_name}")'


@dataclass
class AlterColumn(Operation):
    """Alter a column in a table."""

    table: str
    column_name: str
    new_type: str | None = None
    nullable: bool | None = None
    new_default: Any = None
    drop_default: bool = False
    _old_type: str | None = None
    _old_nullable: bool | None = None
    _old_default: Any = None

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        validate_identifier(self.table, "table")
        validate_identifier(self.column_name, "column")

        driver_name = driver.driver_name

        if driver_name == "postgresql":
            await self._execute_postgresql(conn)
        elif driver_name == "mysql":
            await self._execute_mysql(conn)
        else:
            raise NotImplementedError("SQLite does not support ALTER COLUMN")

    async def _execute_postgresql(self, conn: Any) -> None:
        if self.new_type:
            sql = f"ALTER TABLE {self.table} ALTER COLUMN {self.column_name} TYPE {self.new_type}"
            await conn.execute(sql)

        if self.nullable is not None:
            action = "DROP NOT NULL" if self.nullable else "SET NOT NULL"
            sql = f"ALTER TABLE {self.table} ALTER COLUMN {self.column_name} {action}"
            await conn.execute(sql)

        if self.drop_default:
            sql = (
                f"ALTER TABLE {self.table} ALTER COLUMN {self.column_name} DROP DEFAULT"
            )
            await conn.execute(sql)
        elif self.new_default is not None:
            sql = f"ALTER TABLE {self.table} ALTER COLUMN {self.column_name} SET DEFAULT {self._format_default(self.new_default)}"
            await conn.execute(sql)

    async def _execute_mysql(self, conn: Any) -> None:
        # MySQL MODIFY COLUMN requires full column definition, not partial changes.
        # Changing only nullable or default without providing the full definition
        # would reset other attributes, causing potential data loss.
        if self.nullable is not None:
            raise NotImplementedError(
                "MySQL ALTER COLUMN cannot safely change nullable without full column "
                "definition. Use ExecuteSQL with explicit MODIFY COLUMN syntax instead."
            )
        if self.new_default is not None or self.drop_default:
            raise NotImplementedError(
                "MySQL ALTER COLUMN cannot safely change default without full column "
                "definition. Use ExecuteSQL with explicit MODIFY COLUMN syntax instead."
            )

        if self.new_type:
            # Type-only change is also unsafe without full definition, but we allow it
            # with a warning that other attributes may be reset to defaults.
            # For safe type changes, use ExecuteSQL with explicit MODIFY COLUMN syntax.
            sql = f"ALTER TABLE {self.table} MODIFY COLUMN {self.column_name} {self.new_type}"
            await conn.execute(sql)

    def _format_default(self, value: Any) -> str:
        if isinstance(value, str):
            if value.lower() in ("now()", "current_timestamp"):
                return "CURRENT_TIMESTAMP"
            return f"'{value}'"
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)

    def reverse(self) -> Operation:
        return AlterColumn(
            self.table,
            self.column_name,
            new_type=self._old_type,
            nullable=self._old_nullable,
            new_default=self._old_default if not self.drop_default else None,
            drop_default=self.new_default is not None,
        )

    def to_code(self) -> str:
        parts = [f'"{self.table}"', f'"{self.column_name}"']
        if self.new_type:
            parts.append(f'new_type="{self.new_type}"')
        if self.nullable is not None:
            parts.append(f"nullable={self.nullable}")
        if self.new_default is not None:
            if isinstance(self.new_default, str):
                parts.append(f'new_default="{self.new_default}"')
            else:
                parts.append(f"new_default={self.new_default}")
        if self.drop_default:
            parts.append("drop_default=True")
        return f"op.alter_column({', '.join(parts)})"


@dataclass
class RenameTable(Operation):
    """Rename a table."""

    old_name: str
    new_name: str

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        validate_identifier(self.old_name, "table")
        validate_identifier(self.new_name, "table")

        driver_name = driver.driver_name
        if driver_name == "mysql":
            sql = f"RENAME TABLE {self.old_name} TO {self.new_name}"
        else:
            sql = f"ALTER TABLE {self.old_name} RENAME TO {self.new_name}"
        await conn.execute(sql)

    def reverse(self) -> Operation:
        return RenameTable(self.new_name, self.old_name)

    def to_code(self) -> str:
        return f'op.rename_table("{self.old_name}", "{self.new_name}")'


@dataclass
class RenameColumn(Operation):
    """Rename a column."""

    table: str
    old_name: str
    new_name: str

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        validate_identifier(self.table, "table")
        validate_identifier(self.old_name, "column")
        validate_identifier(self.new_name, "column")

        driver_name = driver.driver_name
        if driver_name == "mysql":
            raise NotImplementedError("MySQL requires column type for CHANGE COLUMN")
        sql = (
            f"ALTER TABLE {self.table} RENAME COLUMN {self.old_name} TO {self.new_name}"
        )
        await conn.execute(sql)

    def reverse(self) -> Operation:
        return RenameColumn(self.table, self.new_name, self.old_name)

    def to_code(self) -> str:
        return f'op.rename_column("{self.table}", "{self.old_name}", "{self.new_name}")'


@dataclass
class CreateIndex(Operation):
    """Create an index."""

    name: str
    table: str
    columns: list[str]
    unique: bool = False
    if_not_exists: bool = False
    where: str | None = None

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        validate_identifier(self.name, "index")
        validate_identifier(self.table, "table")
        for col in self.columns:
            validate_identifier(col, "column")

        driver_name = driver.driver_name

        if self.where and driver_name == "mysql":
            raise ValueError("MySQL does not support partial indexes (WHERE clause)")

        unique_clause = "UNIQUE " if self.unique else ""
        exists_clause = "IF NOT EXISTS " if self.if_not_exists else ""
        columns_sql = ", ".join(self.columns)
        where_clause = f" WHERE {self.where}" if self.where else ""
        sql = f"CREATE {unique_clause}INDEX {exists_clause}{self.name} ON {self.table} ({columns_sql}){where_clause}"
        await conn.execute(sql)

    def reverse(self) -> Operation:
        return DropIndex(
            self.name,
            _index=IndexDef(
                self.name, self.table, self.columns, self.unique, self.where
            ),
        )

    def to_code(self) -> str:
        columns_str = ", ".join(f'"{c}"' for c in self.columns)
        parts = [f'"{self.name}"', f'"{self.table}"', f"[{columns_str}]"]
        if self.unique:
            parts.append("unique=True")
        if self.where:
            escaped_where = self.where.replace('"', '\\"')
            parts.append(f'where="{escaped_where}"')
        return f"op.create_index({', '.join(parts)})"


@dataclass
class DropIndex(Operation):
    """Drop an index."""

    name: str
    if_exists: bool = False
    _index: IndexDef | None = None

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        validate_identifier(self.name, "index")
        exists_clause = "IF EXISTS " if self.if_exists else ""
        sql = f"DROP INDEX {exists_clause}{self.name}"
        await conn.execute(sql)

    def reverse(self) -> Operation:
        if self._index is None:
            raise ValueError("Cannot reverse DropIndex without index definition")
        return CreateIndex(
            self._index.name,
            self._index.table,
            self._index.columns,
            self._index.unique,
            where=self._index.where,
        )

    def to_code(self) -> str:
        return f'op.drop_index("{self.name}")'


@dataclass
class ExecuteSQL(Operation):
    """Execute raw SQL."""

    sql: str
    reverse_sql: str | None = None

    async def execute(self, driver: BaseDriver, conn: Any) -> None:
        await conn.execute(self.sql)

    def reverse(self) -> Operation:
        if self.reverse_sql is None:
            raise ValueError("Cannot reverse ExecuteSQL without reverse_sql")
        return ExecuteSQL(self.reverse_sql, self.sql)

    def to_code(self) -> str:
        escaped_sql = self.sql.replace('"', '\\"')
        if self.reverse_sql:
            escaped_reverse = self.reverse_sql.replace('"', '\\"')
            return f'op.execute("{escaped_sql}", reverse_sql="{escaped_reverse}")'
        return f'op.execute("{escaped_sql}")'
