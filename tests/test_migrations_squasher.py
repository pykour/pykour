"""Tests for migration squasher."""

import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from pykour.db.migrations import op
from pykour.db.migrations.exceptions import SquashRangeError
from pykour.db.migrations.runner import Migration
from pykour.db.migrations.squasher import MigrationSquasher


def create_mock_migration(
    version: str,
    name: str,
    upgrade_func: Any,
    downgrade_func: Any | None = None,
) -> Migration:
    """Create a mock migration with given upgrade/downgrade functions."""
    module = ModuleType(f"{version}_{name}")
    module.upgrade = upgrade_func  # type: ignore[attr-defined]
    module.downgrade = downgrade_func or (lambda: None)  # type: ignore[attr-defined]

    migration = Migration(
        version=version,
        name=name,
        path=Path(f"/fake/{version}_{name}.py"),
    )
    migration.module = module
    return migration


class TestMigrationSquasher:
    """Tests for MigrationSquasher."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.migrations_dir = Path(self.temp_dir)
        self.squasher = MigrationSquasher(self.migrations_dir)

    def test_squash_requires_at_least_two_migrations(self) -> None:
        """Squash should raise error with less than 2 migrations."""

        def upgrade() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        migrations = [
            create_mock_migration("0001", "create_users", upgrade),
        ]

        with pytest.raises(SquashRangeError):
            self.squasher.squash(migrations, "squashed")

    def test_squash_combines_operations(self) -> None:
        """Squash should combine operations from multiple migrations."""

        def upgrade1() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        def downgrade1() -> None:
            op.drop_table("users")

        def upgrade2() -> None:
            op.add_column("users", op.column("email", "VARCHAR(255)"))

        def downgrade2() -> None:
            op.drop_column("users", "email")

        migrations = [
            create_mock_migration("0001", "create_users", upgrade1, downgrade1),
            create_mock_migration("0002", "add_email", upgrade2, downgrade2),
        ]

        result = self.squasher.squash(migrations, "combined")

        assert result.version is not None
        assert result.name == "combined"
        assert len(result.upgrade_ops) == 2
        assert len(result.downgrade_ops) == 2
        assert result.original_versions == ["0001", "0002"]

    def test_squash_with_optimize(self) -> None:
        """Squash with optimize should reduce redundant operations."""

        def upgrade1() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        def downgrade1() -> None:
            op.drop_table("users")

        def upgrade2() -> None:
            op.add_column("users", op.column("email", "VARCHAR(255)", nullable=False))

        def downgrade2() -> None:
            op.drop_column("users", "email")

        migrations = [
            create_mock_migration("0001", "create_users", upgrade1, downgrade1),
            create_mock_migration("0002", "add_email", upgrade2, downgrade2),
        ]

        result = self.squasher.squash(migrations, "optimized", optimize=True)

        # AddColumn should be merged into CreateTable
        assert len(result.upgrade_ops) == 1

    def test_squash_generates_valid_content(self) -> None:
        """Squash should generate valid Python migration content."""

        def upgrade1() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        def downgrade1() -> None:
            op.drop_table("users")

        migrations = [
            create_mock_migration("0001", "create_users", upgrade1, downgrade1),
            create_mock_migration("0002", "also_users", upgrade1, downgrade1),
        ]

        result = self.squasher.squash(migrations, "test")
        content = result.content

        assert "def upgrade():" in content
        assert "def downgrade():" in content
        assert "op.create_table(" in content
        assert "op.drop_table(" in content
        assert "Squashed from migrations:" in content
        assert "0001" in content
        assert "0002" in content

    def test_squash_preserves_operation_order(self) -> None:
        """Squash should preserve the order of operations."""

        def upgrade1() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        def upgrade2() -> None:
            op.create_table(
                "posts",
                op.column("id", "INTEGER", primary_key=True),
            )

        def upgrade3() -> None:
            op.create_index("idx_posts_user", "posts", ["user_id"])

        migrations = [
            create_mock_migration("0001", "users", upgrade1),
            create_mock_migration("0002", "posts", upgrade2),
            create_mock_migration("0003", "index", upgrade3),
        ]

        result = self.squasher.squash(migrations, "combined")

        assert len(result.upgrade_ops) == 3
        assert result.upgrade_ops[0].__class__.__name__ == "CreateTable"
        assert result.upgrade_ops[1].__class__.__name__ == "CreateTable"
        assert result.upgrade_ops[2].__class__.__name__ == "CreateIndex"

    def test_squash_reverses_downgrade_order(self) -> None:
        """Squash should reverse downgrade operations."""

        def upgrade1() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        def downgrade1() -> None:
            op.drop_table("users")

        def upgrade2() -> None:
            op.create_table(
                "posts",
                op.column("id", "INTEGER", primary_key=True),
            )

        def downgrade2() -> None:
            op.drop_table("posts")

        migrations = [
            create_mock_migration("0001", "users", upgrade1, downgrade1),
            create_mock_migration("0002", "posts", upgrade2, downgrade2),
        ]

        result = self.squasher.squash(migrations, "combined")

        # Downgrade order should be reversed (posts first, then users)
        assert len(result.downgrade_ops) == 2
        assert result.downgrade_ops[0].__class__.__name__ == "DropTable"
        assert result.downgrade_ops[1].__class__.__name__ == "DropTable"

    def test_squash_empty_migrations_list(self) -> None:
        """Squash should raise error for empty list."""
        with pytest.raises(SquashRangeError):
            self.squasher.squash([], "empty")

    def test_squash_generates_new_version(self) -> None:
        """Squash should generate a new version number."""

        def upgrade() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        # Create dummy migration files to simulate existing migrations
        (self.migrations_dir / "0001_a.py").write_text("# dummy")
        (self.migrations_dir / "0002_b.py").write_text("# dummy")

        migrations = [
            create_mock_migration("0001", "a", upgrade),
            create_mock_migration("0002", "b", upgrade),
        ]

        result = self.squasher.squash(migrations, "squashed")

        # New version should be after the highest existing version
        assert result.version == "0003"
