"""Tests for migration operation optimizer."""

from pykour.db.migrations.operations import (
    AddColumn,
    CreateIndex,
    CreateTable,
    DropColumn,
    DropIndex,
    DropTable,
)
from pykour.db.migrations.optimizer import OperationOptimizer
from pykour.db.migrations.table import ColumnDef


class TestOperationOptimizer:
    """Tests for OperationOptimizer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.optimizer = OperationOptimizer()

    def test_remove_create_drop_table_pairs(self) -> None:
        """CreateTable + DropTable for same table should be removed."""
        columns = [ColumnDef("id", "INTEGER", primary_key=True)]
        operations = [
            CreateTable("users", columns),
            CreateTable("posts", columns),
            DropTable("users"),
        ]

        result = self.optimizer.optimize(operations)

        assert len(result) == 1
        assert isinstance(result[0], CreateTable)
        assert result[0].name == "posts"

    def test_merge_create_table_with_add_columns(self) -> None:
        """AddColumn after CreateTable should merge into CreateTable."""
        columns = [ColumnDef("id", "INTEGER", primary_key=True)]
        email_col = ColumnDef("email", "VARCHAR(255)", nullable=False)

        operations = [
            CreateTable("users", columns),
            AddColumn("users", email_col),
        ]

        result = self.optimizer.optimize(operations)

        assert len(result) == 1
        assert isinstance(result[0], CreateTable)
        assert len(result[0].columns) == 2
        assert result[0].columns[0].name == "id"
        assert result[0].columns[1].name == "email"

    def test_add_column_to_different_table_not_merged(self) -> None:
        """AddColumn to different table should not be merged."""
        columns = [ColumnDef("id", "INTEGER", primary_key=True)]
        title_col = ColumnDef("title", "VARCHAR(255)", nullable=False)

        operations = [
            CreateTable("users", columns),
            AddColumn("posts", title_col),
        ]

        result = self.optimizer.optimize(operations)

        assert len(result) == 2

    def test_remove_add_drop_column_pairs(self) -> None:
        """AddColumn + DropColumn for same column should be removed."""
        email_col = ColumnDef("email", "VARCHAR(255)")

        operations = [
            AddColumn("users", email_col),
            AddColumn("users", ColumnDef("name", "VARCHAR(100)")),
            DropColumn("users", "email"),
        ]

        result = self.optimizer.optimize(operations)

        assert len(result) == 1
        assert isinstance(result[0], AddColumn)
        assert result[0].column.name == "name"

    def test_remove_create_drop_index_pairs(self) -> None:
        """CreateIndex + DropIndex for same index should be removed."""
        operations = [
            CreateIndex("idx_users_email", "users", ["email"]),
            CreateIndex("idx_users_name", "users", ["name"]),
            DropIndex("idx_users_email"),
        ]

        result = self.optimizer.optimize(operations)

        assert len(result) == 1
        assert isinstance(result[0], CreateIndex)
        assert result[0].name == "idx_users_name"

    def test_complex_optimization(self) -> None:
        """Multiple optimization rules should be applied."""
        columns = [ColumnDef("id", "INTEGER", primary_key=True)]
        email_col = ColumnDef("email", "VARCHAR(255)")

        operations = [
            CreateTable("users", columns),
            AddColumn("users", email_col),
            CreateIndex("idx_users_email", "users", ["email"]),
            DropColumn("users", "email"),
            DropIndex("idx_users_email"),
        ]

        result = self.optimizer.optimize(operations)

        # Optimization steps:
        # 1. _remove_create_drop_table_pairs: no pairs, unchanged
        # 2. _merge_create_table_with_add_columns: CreateTable gets email column, AddColumn removed
        # 3. _remove_add_drop_column_pairs: no AddColumn left to pair with DropColumn
        # 4. _remove_create_drop_index_pairs: CreateIndex + DropIndex removed
        # Result: CreateTable(users, [id, email]), DropColumn(users, email)
        assert len(result) == 2
        assert isinstance(result[0], CreateTable)
        assert isinstance(result[1], DropColumn)

    def test_empty_operations(self) -> None:
        """Empty operations list should return empty."""
        result = self.optimizer.optimize([])
        assert result == []

    def test_no_optimization_needed(self) -> None:
        """Operations that don't need optimization should remain unchanged."""
        columns = [ColumnDef("id", "INTEGER", primary_key=True)]
        operations = [
            CreateTable("users", columns),
            CreateTable("posts", columns),
            CreateIndex("idx_users_email", "users", ["email"]),
        ]

        result = self.optimizer.optimize(operations)

        assert len(result) == 3
