"""Tests for migration analyzer."""

from pathlib import Path
from types import ModuleType
from typing import Any


from pykour.db.migrations import op
from pykour.db.migrations.analyzer import MigrationAnalyzer
from pykour.db.migrations.runner import Migration


def create_mock_migration(
    version: str,
    name: str,
    upgrade_func: Any,
) -> Migration:
    """Create a mock migration with a given upgrade function."""
    module = ModuleType(f"{version}_{name}")
    module.upgrade = upgrade_func  # type: ignore[attr-defined]
    module.downgrade = lambda: None  # type: ignore[attr-defined]

    migration = Migration(
        version=version,
        name=name,
        path=Path(f"/fake/{version}_{name}.py"),
    )
    migration.module = module
    return migration


class TestMigrationAnalyzer:
    """Tests for MigrationAnalyzer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.analyzer = MigrationAnalyzer()

    def test_analyze_create_table(self) -> None:
        """Analyze should detect tables from CreateTable operations."""

        def upgrade() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        migration = create_mock_migration("0001", "create_users", upgrade)
        tables = self.analyzer.analyze(migration)

        assert tables == {"users"}

    def test_analyze_add_column(self) -> None:
        """Analyze should detect tables from AddColumn operations."""

        def upgrade() -> None:
            op.add_column("users", op.column("email", "VARCHAR(255)"))

        migration = create_mock_migration("0002", "add_email", upgrade)
        tables = self.analyzer.analyze(migration)

        assert tables == {"users"}

    def test_analyze_drop_table(self) -> None:
        """Analyze should detect tables from DropTable operations."""

        def upgrade() -> None:
            op.drop_table("old_table")

        migration = create_mock_migration("0003", "drop_old", upgrade)
        tables = self.analyzer.analyze(migration)

        assert tables == {"old_table"}

    def test_analyze_rename_table(self) -> None:
        """Analyze should detect both old and new tables from RenameTable."""

        def upgrade() -> None:
            op.rename_table("old_name", "new_name")

        migration = create_mock_migration("0004", "rename_table", upgrade)
        tables = self.analyzer.analyze(migration)

        assert tables == {"old_name", "new_name"}

    def test_analyze_create_index(self) -> None:
        """Analyze should detect tables from CreateIndex operations."""

        def upgrade() -> None:
            op.create_index("idx_users_email", "users", ["email"])

        migration = create_mock_migration("0005", "add_index", upgrade)
        tables = self.analyzer.analyze(migration)

        assert tables == {"users"}

    def test_analyze_multiple_tables(self) -> None:
        """Analyze should detect multiple tables."""

        def upgrade() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )
            op.create_table(
                "posts",
                op.column("id", "INTEGER", primary_key=True),
            )

        migration = create_mock_migration("0006", "create_tables", upgrade)
        tables = self.analyzer.analyze(migration)

        assert tables == {"users", "posts"}

    def test_analyze_no_tables(self) -> None:
        """Analyze should return empty set for migrations with no tables."""

        def upgrade() -> None:
            op.execute("SELECT 1")

        migration = create_mock_migration("0007", "raw_sql", upgrade)
        tables = self.analyzer.analyze(migration)

        assert tables == set()

    def test_group_by_table_single_table_migrations(self) -> None:
        """Migrations affecting single table should be grouped by table."""

        def upgrade_users() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        def upgrade_posts() -> None:
            op.create_table(
                "posts",
                op.column("id", "INTEGER", primary_key=True),
            )

        migrations = [
            create_mock_migration("0001", "create_users", upgrade_users),
            create_mock_migration("0002", "create_posts", upgrade_posts),
        ]

        groups = self.analyzer.group_by_table(migrations)

        assert "users" in groups
        assert "posts" in groups
        assert len(groups["users"]) == 1
        assert len(groups["posts"]) == 1
        assert groups["users"][0].version == "0001"
        assert groups["posts"][0].version == "0002"

    def test_group_by_table_multiple_tables(self) -> None:
        """Migrations affecting multiple tables should be grouped separately."""

        def upgrade_both() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )
            op.create_table(
                "posts",
                op.column("id", "INTEGER", primary_key=True),
            )

        migrations = [
            create_mock_migration("0001", "create_tables", upgrade_both),
        ]

        groups = self.analyzer.group_by_table(migrations)

        assert "multiple tables" in groups
        assert len(groups["multiple tables"]) == 1

    def test_group_by_table_no_tables(self) -> None:
        """Migrations with no tables should be grouped under '(no tables)'."""

        def upgrade_empty() -> None:
            op.execute("SELECT 1")

        migrations = [
            create_mock_migration("0001", "raw_sql", upgrade_empty),
        ]

        groups = self.analyzer.group_by_table(migrations)

        assert "(no tables)" in groups
        assert len(groups["(no tables)"]) == 1

    def test_get_table_info_single_table(self) -> None:
        """get_table_info should return table name for single-table migration."""

        def upgrade() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )

        migration = create_mock_migration("0001", "create_users", upgrade)
        info = self.analyzer.get_table_info(migration)

        assert info == "users"

    def test_get_table_info_multiple_tables(self) -> None:
        """get_table_info should return comma-separated names for multiple tables."""

        def upgrade() -> None:
            op.create_table(
                "users",
                op.column("id", "INTEGER", primary_key=True),
            )
            op.add_column("posts", op.column("title", "VARCHAR(255)"))

        migration = create_mock_migration("0001", "schema", upgrade)
        info = self.analyzer.get_table_info(migration)

        assert info == "posts, users"

    def test_get_table_info_no_tables(self) -> None:
        """get_table_info should return '(no tables)' for empty migration."""

        def upgrade() -> None:
            op.execute("SELECT 1")

        migration = create_mock_migration("0001", "raw", upgrade)
        info = self.analyzer.get_table_info(migration)

        assert info == "(no tables)"
