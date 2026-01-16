"""Tests for migration operations."""

import pytest

from pykour.db.migrations.operations import (
    AddColumn,
    CreateIndex,
    CreateTable,
    DropColumn,
    DropIndex,
    DropTable,
    ExecuteSQL,
    RenameColumn,
    RenameTable,
)
from pykour.db.migrations.table import ColumnDef


class TestCreateTable:
    """Tests for CreateTable operation."""

    def test_to_code(self) -> None:
        """CreateTable should generate correct Python code."""
        columns = [
            ColumnDef("id", "INTEGER", primary_key=True, autoincrement=True),
            ColumnDef("name", "VARCHAR(100)", nullable=False),
        ]
        op = CreateTable("users", columns)
        code = op.to_code()

        assert "op.create_table(" in code
        assert '"users"' in code
        assert (
            'op.column("id", "INTEGER", primary_key=True, autoincrement=True)' in code
        )
        assert 'op.column("name", "VARCHAR(100)", nullable=False)' in code

    def test_reverse(self) -> None:
        """CreateTable reverse should be DropTable."""
        columns = [ColumnDef("id", "INTEGER", primary_key=True)]
        op = CreateTable("users", columns)
        reverse = op.reverse()

        assert isinstance(reverse, DropTable)
        assert reverse.name == "users"


class TestDropTable:
    """Tests for DropTable operation."""

    def test_to_code(self) -> None:
        """DropTable should generate correct Python code."""
        op = DropTable("users")
        code = op.to_code()

        assert 'op.drop_table("users")' == code


class TestAddColumn:
    """Tests for AddColumn operation."""

    def test_to_code(self) -> None:
        """AddColumn should generate correct Python code."""
        col = ColumnDef("email", "VARCHAR(255)", nullable=False, unique=True)
        op = AddColumn("users", col)
        code = op.to_code()

        assert 'op.add_column("users"' in code
        assert '"email"' in code
        assert '"VARCHAR(255)"' in code
        assert "nullable=False" in code
        assert "unique=True" in code

    def test_reverse(self) -> None:
        """AddColumn reverse should be DropColumn."""
        col = ColumnDef("email", "VARCHAR(255)")
        op = AddColumn("users", col)
        reverse = op.reverse()

        assert isinstance(reverse, DropColumn)
        assert reverse.table == "users"
        assert reverse.column_name == "email"


class TestDropColumn:
    """Tests for DropColumn operation."""

    def test_to_code(self) -> None:
        """DropColumn should generate correct Python code."""
        op = DropColumn("users", "email")
        code = op.to_code()

        assert 'op.drop_column("users", "email")' == code


class TestRenameTable:
    """Tests for RenameTable operation."""

    def test_to_code(self) -> None:
        """RenameTable should generate correct Python code."""
        op = RenameTable("users", "accounts")
        code = op.to_code()

        assert 'op.rename_table("users", "accounts")' == code

    def test_reverse(self) -> None:
        """RenameTable reverse should swap names."""
        op = RenameTable("users", "accounts")
        reverse = op.reverse()

        assert isinstance(reverse, RenameTable)
        assert reverse.old_name == "accounts"
        assert reverse.new_name == "users"


class TestRenameColumn:
    """Tests for RenameColumn operation."""

    def test_to_code(self) -> None:
        """RenameColumn should generate correct Python code."""
        op = RenameColumn("users", "name", "full_name")
        code = op.to_code()

        assert 'op.rename_column("users", "name", "full_name")' == code

    def test_reverse(self) -> None:
        """RenameColumn reverse should swap names."""
        op = RenameColumn("users", "name", "full_name")
        reverse = op.reverse()

        assert isinstance(reverse, RenameColumn)
        assert reverse.old_name == "full_name"
        assert reverse.new_name == "name"


class TestCreateIndex:
    """Tests for CreateIndex operation."""

    def test_to_code(self) -> None:
        """CreateIndex should generate correct Python code."""
        op = CreateIndex("idx_users_email", "users", ["email"])
        code = op.to_code()

        assert 'op.create_index("idx_users_email", "users", ["email"])' == code

    def test_to_code_unique(self) -> None:
        """CreateIndex should include unique flag."""
        op = CreateIndex("idx_users_email", "users", ["email"], unique=True)
        code = op.to_code()

        assert "unique=True" in code

    def test_reverse(self) -> None:
        """CreateIndex reverse should be DropIndex."""
        op = CreateIndex("idx_users_email", "users", ["email"])
        reverse = op.reverse()

        assert isinstance(reverse, DropIndex)
        assert reverse.name == "idx_users_email"

    def test_to_code_with_where(self) -> None:
        """CreateIndex should include WHERE clause."""
        op = CreateIndex("idx_active", "users", ["email"], where="active = 1")
        code = op.to_code()

        assert 'where="active = 1"' in code

    def test_to_code_unique_with_where(self) -> None:
        """CreateIndex should include both unique and WHERE clause."""
        op = CreateIndex(
            "idx_active", "users", ["email"], unique=True, where="active = 1"
        )
        code = op.to_code()

        assert "unique=True" in code
        assert 'where="active = 1"' in code

    def test_reverse_with_where(self) -> None:
        """CreateIndex with WHERE reverse should preserve WHERE clause."""
        op = CreateIndex("idx_active", "users", ["email"], where="active = 1")
        reverse = op.reverse()

        assert isinstance(reverse, DropIndex)
        assert reverse._index is not None
        assert reverse._index.where == "active = 1"


class TestDropIndex:
    """Tests for DropIndex operation."""

    def test_to_code(self) -> None:
        """DropIndex should generate correct Python code."""
        op = DropIndex("idx_users_email")
        code = op.to_code()

        assert 'op.drop_index("idx_users_email")' == code


class TestExecuteSQL:
    """Tests for ExecuteSQL operation."""

    def test_to_code(self) -> None:
        """ExecuteSQL should generate correct Python code."""
        op = ExecuteSQL(
            "CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1"
        )
        code = op.to_code()

        assert "op.execute(" in code
        assert "CREATE VIEW" in code

    def test_to_code_with_reverse(self) -> None:
        """ExecuteSQL with reverse should include reverse_sql."""
        op = ExecuteSQL(
            "CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1",
            reverse_sql="DROP VIEW active_users",
        )
        code = op.to_code()

        assert "reverse_sql=" in code
        assert "DROP VIEW" in code

    def test_reverse(self) -> None:
        """ExecuteSQL reverse should swap SQL."""
        op = ExecuteSQL("CREATE VIEW v", reverse_sql="DROP VIEW v")
        reverse = op.reverse()

        assert isinstance(reverse, ExecuteSQL)
        assert reverse.sql == "DROP VIEW v"
        assert reverse.reverse_sql == "CREATE VIEW v"

    def test_reverse_without_reverse_sql(self) -> None:
        """ExecuteSQL without reverse_sql should raise."""
        op = ExecuteSQL("SELECT 1")

        with pytest.raises(ValueError):
            op.reverse()
