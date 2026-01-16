"""Operation helper functions for migrations.

This module provides a convenient API for writing migration files:

    from pykour.db.migrations import op

    def upgrade():
        op.create_table(
            "users",
            op.column("id", "INTEGER", primary_key=True, autoincrement=True),
            op.column("name", "VARCHAR(100)", nullable=False),
        )

    def downgrade():
        op.drop_table("users")
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pykour.db.migrations.operations import (
    AddColumn,
    AlterColumn,
    CreateIndex,
    CreateTable,
    DropColumn,
    DropIndex,
    DropTable,
    ExecuteSQL,
    Operation,
    RenameColumn,
    RenameTable,
)
from pykour.db.migrations.access_policy_ops import (
    AlterAccessPolicy,
    CreateAccessPolicy,
    DropAccessPolicy,
)
from pykour.db.migrations.table import ColumnDef

if TYPE_CHECKING:
    from pykour.db.drivers.base import BaseDriver


@dataclass
class OpContext:
    """Context for migration operations."""

    driver: BaseDriver
    conn: Any
    operations: list[Operation]


_context: ContextVar[OpContext | None] = ContextVar("op_context", default=None)


def get_context() -> OpContext:
    """Get the current operation context."""
    ctx = _context.get()
    if ctx is None:
        raise RuntimeError(
            "No migration context. Operations must be run inside a migration."
        )
    return ctx


def set_context(ctx: OpContext | None) -> None:
    """Set the operation context."""
    _context.set(ctx)


def column(
    name: str,
    type_sql: str,
    *,
    primary_key: bool = False,
    nullable: bool = True,
    unique: bool = False,
    default: Any = None,
    autoincrement: bool = False,
) -> ColumnDef:
    """Create a column definition.

    Args:
        name: Column name.
        type_sql: SQL type string (e.g., "INTEGER", "VARCHAR(100)").
        primary_key: Whether this is the primary key.
        nullable: Whether the column allows NULL.
        unique: Whether the column has a unique constraint.
        default: Default value.
        autoincrement: Whether to auto-increment.

    Returns:
        ColumnDef instance.
    """
    return ColumnDef(
        name=name,
        type_sql=type_sql,
        primary_key=primary_key,
        nullable=nullable,
        unique=unique,
        default=default,
        autoincrement=autoincrement,
    )


def create_table(
    name: str,
    *columns: ColumnDef,
    if_not_exists: bool = False,
) -> None:
    """Create a new table.

    Args:
        name: Table name.
        *columns: Column definitions (use op.column()).
        if_not_exists: Add IF NOT EXISTS clause.
    """
    ctx = get_context()
    op = CreateTable(name, list(columns), if_not_exists)
    ctx.operations.append(op)


def drop_table(name: str, *, if_exists: bool = False) -> None:
    """Drop a table.

    Args:
        name: Table name.
        if_exists: Add IF EXISTS clause.
    """
    ctx = get_context()
    op = DropTable(name, if_exists)
    ctx.operations.append(op)


def add_column(table: str, col: ColumnDef) -> None:
    """Add a column to a table.

    Args:
        table: Table name.
        col: Column definition (use op.column()).
    """
    ctx = get_context()
    op = AddColumn(table, col)
    ctx.operations.append(op)


def drop_column(table: str, column_name: str) -> None:
    """Drop a column from a table.

    Args:
        table: Table name.
        column_name: Column name to drop.
    """
    ctx = get_context()
    op = DropColumn(table, column_name)
    ctx.operations.append(op)


def alter_column(
    table: str,
    column_name: str,
    *,
    new_type: str | None = None,
    nullable: bool | None = None,
    new_default: Any = None,
    drop_default: bool = False,
) -> None:
    """Alter a column in a table.

    Args:
        table: Table name.
        column_name: Column name.
        new_type: New SQL type.
        nullable: New nullable setting.
        new_default: New default value.
        drop_default: Drop the default value.
    """
    ctx = get_context()
    op = AlterColumn(
        table,
        column_name,
        new_type=new_type,
        nullable=nullable,
        new_default=new_default,
        drop_default=drop_default,
    )
    ctx.operations.append(op)


def rename_table(old_name: str, new_name: str) -> None:
    """Rename a table.

    Args:
        old_name: Current table name.
        new_name: New table name.
    """
    ctx = get_context()
    op = RenameTable(old_name, new_name)
    ctx.operations.append(op)


def rename_column(table: str, old_name: str, new_name: str) -> None:
    """Rename a column.

    Args:
        table: Table name.
        old_name: Current column name.
        new_name: New column name.
    """
    ctx = get_context()
    op = RenameColumn(table, old_name, new_name)
    ctx.operations.append(op)


def create_index(
    name: str,
    table: str,
    columns: list[str],
    *,
    unique: bool = False,
    if_not_exists: bool = False,
    where: str | None = None,
) -> None:
    """Create an index.

    Args:
        name: Index name.
        table: Table name.
        columns: Column names to index.
        unique: Create a unique index.
        if_not_exists: Add IF NOT EXISTS clause.
        where: WHERE clause for partial index (SQLite/PostgreSQL only).

    Note:
        MySQL does not support partial indexes with WHERE clause.
        An error will be raised at execution time if `where` is specified
        for a MySQL database.
    """
    ctx = get_context()
    op = CreateIndex(name, table, columns, unique, if_not_exists, where)
    ctx.operations.append(op)


def drop_index(name: str, *, if_exists: bool = False) -> None:
    """Drop an index.

    Args:
        name: Index name.
        if_exists: Add IF EXISTS clause.
    """
    ctx = get_context()
    op = DropIndex(name, if_exists)
    ctx.operations.append(op)


def execute(sql: str, *, reverse_sql: str | None = None) -> None:
    """Execute raw SQL.

    Args:
        sql: SQL to execute.
        reverse_sql: SQL to execute when rolling back (optional).
    """
    ctx = get_context()
    op = ExecuteSQL(sql, reverse_sql)
    ctx.operations.append(op)


# Access Policy operations


def create_access_policy(
    table: str,
    name: str,
    *,
    select: list[str] | None = None,
    insert: list[str] | None = None,
    update: list[str] | None = None,
    delete: list[str] | None = None,
    auto_set: dict[str, str] | None = None,
    bypass_roles: list[str] | None = None,
) -> None:
    """Create an access policy on a table.

    For PostgreSQL, creates native RLS policies.
    For MySQL/SQLite, stores policy metadata for application-level enforcement.

    Args:
        table: Table name.
        name: Policy name.
        select: List of conditions for SELECT queries.
        insert: List of conditions for INSERT queries.
        update: List of conditions for UPDATE queries.
        delete: List of conditions for DELETE queries.
        auto_set: Dict mapping columns to context keys for auto-insert.
        bypass_roles: List of roles that bypass this policy.

    Example:
        op.create_access_policy(
            "orders",
            "orders_tenant_policy",
            select=["tenant_id = :tenant_id"],
            insert=["tenant_id = :tenant_id"],
            auto_set={"tenant_id": ":tenant_id"},
        )
    """
    ctx = get_context()
    op = CreateAccessPolicy(
        table,
        name,
        select=select or [],
        insert=insert or [],
        update=update or [],
        delete=delete or [],
        auto_set=auto_set or {},
        bypass_roles=bypass_roles or [],
    )
    ctx.operations.append(op)


def drop_access_policy(table: str, name: str) -> None:
    """Drop an access policy from a table.

    Args:
        table: Table name.
        name: Policy name.
    """
    ctx = get_context()
    op = DropAccessPolicy(table, name)
    ctx.operations.append(op)


def alter_access_policy(
    table: str,
    name: str,
    *,
    new_select: list[str] | None = None,
    new_insert: list[str] | None = None,
    new_update: list[str] | None = None,
    new_delete: list[str] | None = None,
    new_auto_set: dict[str, str] | None = None,
    new_bypass_roles: list[str] | None = None,
) -> None:
    """Alter an existing access policy.

    Args:
        table: Table name.
        name: Policy name.
        new_select: New SELECT conditions (None to keep existing).
        new_insert: New INSERT conditions (None to keep existing).
        new_update: New UPDATE conditions (None to keep existing).
        new_delete: New DELETE conditions (None to keep existing).
        new_auto_set: New auto_set mapping (None to keep existing).
        new_bypass_roles: New bypass roles (None to keep existing).

    Example:
        op.alter_access_policy(
            "orders",
            "orders_tenant_policy",
            new_select=["tenant_id = :tenant_id", "active = true"],
        )
    """
    ctx = get_context()
    op = AlterAccessPolicy(
        table,
        name,
        new_select=new_select,
        new_insert=new_insert,
        new_update=new_update,
        new_delete=new_delete,
        new_auto_set=new_auto_set,
        new_bypass_roles=new_bypass_roles,
    )
    ctx.operations.append(op)
