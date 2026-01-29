"""Column presets for common patterns.

This module provides reusable column group definitions for common patterns
like timestamps, audit fields, and soft delete.

Example usage:

    from pykour.db.migrations import op
    from pykour.db.migrations.presets import timestamps, soft_delete

    def upgrade():
        op.create_table(
            "users",
            op.column("id", "INTEGER", primary_key=True, autoincrement=True),
            timestamps,  # Adds created_at and updated_at
            op.column("name", "VARCHAR(100)", nullable=False),
            soft_delete,  # Adds is_deleted
        )

Users can also define their own ColumnGroup:

    from pykour.db.migrations.presets import ColumnGroup

    tenant_columns = ColumnGroup("tenant", [
        op.column("tenant_id", "VARCHAR(36)", nullable=False),
        op.column("organization_id", "VARCHAR(36)", nullable=True),
    ])
"""

from __future__ import annotations

from pykour.db.migrations.table import ColumnDef


class ColumnGroup:
    """A reusable collection of column definitions.

    Can be used directly in op.create_table() alongside op.column():

        op.create_table(
            "users",
            op.column("id", "INTEGER", primary_key=True),
            timestamps,  # ColumnGroup
            op.column("name", "VARCHAR(100)"),
        )

    Users can define their own ColumnGroup:

        tenant_columns = ColumnGroup("tenant", [
            ColumnDef("tenant_id", "VARCHAR(36)", nullable=False),
        ])
    """

    def __init__(self, name: str, columns: list[ColumnDef]) -> None:
        """Initialize a ColumnGroup.

        Args:
            name: A descriptive name for this group of columns.
            columns: List of ColumnDef instances.
        """
        self.name = name
        self.columns = columns

    def __repr__(self) -> str:
        return f"ColumnGroup({self.name!r})"


# Built-in presets

timestamps = ColumnGroup(
    "timestamps",
    [
        ColumnDef(
            "created_at", "TIMESTAMP", nullable=False, default="CURRENT_TIMESTAMP"
        ),
        ColumnDef("updated_at", "TIMESTAMP", nullable=True),
    ],
)

created = ColumnGroup(
    "created",
    [
        ColumnDef(
            "created_at", "TIMESTAMP", nullable=False, default="CURRENT_TIMESTAMP"
        ),
        ColumnDef("created_by", "VARCHAR(100)", nullable=True),
    ],
)

updated = ColumnGroup(
    "updated",
    [
        ColumnDef("updated_at", "TIMESTAMP", nullable=True),
        ColumnDef("updated_by", "VARCHAR(100)", nullable=True),
    ],
)

audit = ColumnGroup(
    "audit",
    [
        ColumnDef(
            "created_at", "TIMESTAMP", nullable=False, default="CURRENT_TIMESTAMP"
        ),
        ColumnDef("created_by", "VARCHAR(100)", nullable=True),
        ColumnDef("updated_at", "TIMESTAMP", nullable=True),
        ColumnDef("updated_by", "VARCHAR(100)", nullable=True),
    ],
)

soft_delete = ColumnGroup(
    "soft_delete",
    [
        ColumnDef("is_deleted", "BOOLEAN", nullable=False, default=False),
    ],
)
