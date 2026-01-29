"""Tests for migration presets module."""

from typing import Any, cast

import pytest

from pykour.db.migrations import op
from pykour.db.migrations.presets import (
    ColumnGroup,
    timestamps,
    created,
    updated,
    audit,
    soft_delete,
)
from pykour.db.migrations.table import ColumnDef
from pykour.db.migrations.op import OpContext, set_context


@pytest.fixture
def mock_context():
    """Create a mock migration context."""
    ctx = OpContext(
        driver=cast(Any, None),
        conn=cast(Any, None),
        operations=[],
    )
    set_context(ctx)
    yield ctx
    set_context(None)


class TestColumnGroup:
    """Tests for ColumnGroup class."""

    def test_init(self):
        """Test ColumnGroup initialization."""
        columns = [
            ColumnDef("col1", "VARCHAR(100)", nullable=False),
            ColumnDef("col2", "INTEGER", nullable=True),
        ]
        group = ColumnGroup("test_group", columns)

        assert group.name == "test_group"
        assert group.columns == columns
        assert len(group.columns) == 2

    def test_repr(self):
        """Test ColumnGroup string representation."""
        group = ColumnGroup("my_group", [])
        assert repr(group) == "ColumnGroup('my_group')"

    def test_user_defined_column_group(self):
        """Test that users can define their own ColumnGroup."""
        tenant_columns = ColumnGroup(
            "tenant",
            [
                ColumnDef("tenant_id", "VARCHAR(36)", nullable=False),
                ColumnDef("organization_id", "VARCHAR(36)", nullable=True),
            ],
        )

        assert tenant_columns.name == "tenant"
        assert len(tenant_columns.columns) == 2
        assert tenant_columns.columns[0].name == "tenant_id"
        assert tenant_columns.columns[1].name == "organization_id"


class TestBuiltinPresets:
    """Tests for built-in preset definitions."""

    def test_timestamps_preset(self):
        """Test timestamps preset contains correct columns."""
        assert timestamps.name == "timestamps"
        assert len(timestamps.columns) == 2

        created_at = timestamps.columns[0]
        assert created_at.name == "created_at"
        assert created_at.type_sql == "TIMESTAMP"
        assert created_at.nullable is False
        assert created_at.default == "CURRENT_TIMESTAMP"

        updated_at = timestamps.columns[1]
        assert updated_at.name == "updated_at"
        assert updated_at.type_sql == "TIMESTAMP"
        assert updated_at.nullable is True

    def test_created_preset(self):
        """Test created preset contains correct columns."""
        assert created.name == "created"
        assert len(created.columns) == 2

        created_at = created.columns[0]
        assert created_at.name == "created_at"
        assert created_at.type_sql == "TIMESTAMP"
        assert created_at.nullable is False
        assert created_at.default == "CURRENT_TIMESTAMP"

        created_by = created.columns[1]
        assert created_by.name == "created_by"
        assert created_by.type_sql == "VARCHAR(100)"
        assert created_by.nullable is True

    def test_updated_preset(self):
        """Test updated preset contains correct columns."""
        assert updated.name == "updated"
        assert len(updated.columns) == 2

        updated_at = updated.columns[0]
        assert updated_at.name == "updated_at"
        assert updated_at.type_sql == "TIMESTAMP"
        assert updated_at.nullable is True

        updated_by = updated.columns[1]
        assert updated_by.name == "updated_by"
        assert updated_by.type_sql == "VARCHAR(100)"
        assert updated_by.nullable is True

    def test_audit_preset(self):
        """Test audit preset contains correct columns."""
        assert audit.name == "audit"
        assert len(audit.columns) == 4

        column_names = [c.name for c in audit.columns]
        assert column_names == ["created_at", "created_by", "updated_at", "updated_by"]

    def test_soft_delete_preset(self):
        """Test soft_delete preset contains correct columns."""
        assert soft_delete.name == "soft_delete"
        assert len(soft_delete.columns) == 1

        is_deleted = soft_delete.columns[0]
        assert is_deleted.name == "is_deleted"
        assert is_deleted.type_sql == "BOOLEAN"
        assert is_deleted.nullable is False
        assert is_deleted.default is False


class TestCreateTableWithPresets:
    """Tests for op.create_table with ColumnGroup support."""

    def test_create_table_with_single_preset(self, mock_context):
        """Test create_table with a single preset."""
        op.create_table(
            "users",
            op.column("id", "INTEGER", primary_key=True, autoincrement=True),
            timestamps,
            op.column("name", "VARCHAR(100)", nullable=False),
        )

        assert len(mock_context.operations) == 1
        create_op = mock_context.operations[0]
        assert create_op.name == "users"
        assert len(create_op.columns) == 4

        column_names = [c.name for c in create_op.columns]
        assert column_names == ["id", "created_at", "updated_at", "name"]

    def test_create_table_with_multiple_presets(self, mock_context):
        """Test create_table with multiple presets."""
        op.create_table(
            "orders",
            op.column("id", "INTEGER", primary_key=True, autoincrement=True),
            timestamps,
            op.column("total", "DECIMAL(10,2)", nullable=False),
            soft_delete,
        )

        assert len(mock_context.operations) == 1
        create_op = mock_context.operations[0]
        assert len(create_op.columns) == 5

        column_names = [c.name for c in create_op.columns]
        assert column_names == ["id", "created_at", "updated_at", "total", "is_deleted"]

    def test_create_table_with_user_defined_preset(self, mock_context):
        """Test create_table with user-defined ColumnGroup."""
        tenant_columns = ColumnGroup(
            "tenant",
            [
                ColumnDef("tenant_id", "VARCHAR(36)", nullable=False),
                ColumnDef("organization_id", "VARCHAR(36)", nullable=True),
            ],
        )

        op.create_table(
            "orders",
            op.column("id", "INTEGER", primary_key=True, autoincrement=True),
            tenant_columns,
            timestamps,
            op.column("total", "DECIMAL(10,2)", nullable=False),
        )

        assert len(mock_context.operations) == 1
        create_op = mock_context.operations[0]
        assert len(create_op.columns) == 6

        column_names = [c.name for c in create_op.columns]
        assert column_names == [
            "id",
            "tenant_id",
            "organization_id",
            "created_at",
            "updated_at",
            "total",
        ]

    def test_create_table_without_presets(self, mock_context):
        """Test create_table still works without presets."""
        op.create_table(
            "simple",
            op.column("id", "INTEGER", primary_key=True),
            op.column("value", "TEXT"),
        )

        assert len(mock_context.operations) == 1
        create_op = mock_context.operations[0]
        assert len(create_op.columns) == 2

        column_names = [c.name for c in create_op.columns]
        assert column_names == ["id", "value"]

    def test_create_table_with_if_not_exists(self, mock_context):
        """Test create_table with if_not_exists and presets."""
        op.create_table(
            "users",
            op.column("id", "INTEGER", primary_key=True),
            timestamps,
            if_not_exists=True,
        )

        assert len(mock_context.operations) == 1
        create_op = mock_context.operations[0]
        assert create_op.if_not_exists is True
        assert len(create_op.columns) == 3

    def test_preset_columns_preserve_properties(self, mock_context):
        """Test that preset columns preserve their properties."""
        op.create_table(
            "test",
            op.column("id", "INTEGER", primary_key=True),
            timestamps,
        )

        create_op = mock_context.operations[0]
        created_at_col = create_op.columns[1]

        assert created_at_col.name == "created_at"
        assert created_at_col.type_sql == "TIMESTAMP"
        assert created_at_col.nullable is False
        assert created_at_col.default == "CURRENT_TIMESTAMP"


class TestPresetImports:
    """Tests for preset imports from pykour.db.migrations."""

    def test_imports_from_migrations_module(self):
        """Test that presets can be imported from migrations module."""
        from pykour.db.migrations import (
            ColumnGroup,
            timestamps,
            created,
            updated,
            audit,
            soft_delete,
        )

        assert ColumnGroup is not None
        assert timestamps is not None
        assert created is not None
        assert updated is not None
        assert audit is not None
        assert soft_delete is not None
