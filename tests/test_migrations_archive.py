"""Tests for migration archive functionality."""

import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any


from pykour.db.migrations import op
from pykour.db.migrations.exceptions import ArchiveBoundaryError
from pykour.db.migrations.runner import Migration, MigrationRunner


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


class DummyDb:
    """Dummy database for file-only mode."""

    _driver = None


class TestArchiveBoundary:
    """Tests for archive boundary functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.migrations_dir = Path(self.temp_dir)
        self.runner = MigrationRunner(DummyDb(), self.migrations_dir)  # type: ignore[arg-type]

    def test_get_archive_boundary_no_archive(self) -> None:
        """Should return None when no archive folder exists."""
        boundary = self.runner.get_archive_boundary()
        assert boundary is None

    def test_get_archive_boundary_empty_archive(self) -> None:
        """Should return None when archive folder is empty."""
        archive_dir = self.migrations_dir / "archive"
        archive_dir.mkdir()

        boundary = self.runner.get_archive_boundary()
        assert boundary is None

    def test_get_archive_boundary_with_migrations(self) -> None:
        """Should return highest version in archive folder."""
        archive_dir = self.migrations_dir / "archive"
        archive_dir.mkdir()

        (archive_dir / "0001_create_users.py").write_text("# migration")
        (archive_dir / "0002_add_email.py").write_text("# migration")
        (archive_dir / "0003_add_posts.py").write_text("# migration")

        boundary = self.runner.get_archive_boundary()
        assert boundary == "0003"

    def test_get_archive_boundary_ignores_underscore_files(self) -> None:
        """Should ignore files starting with underscore."""
        archive_dir = self.migrations_dir / "archive"
        archive_dir.mkdir()

        (archive_dir / "0001_create_users.py").write_text("# migration")
        (archive_dir / "__init__.py").write_text("# init")
        (archive_dir / "_helper.py").write_text("# helper")

        boundary = self.runner.get_archive_boundary()
        assert boundary == "0001"

    def test_discover_archived_no_archive(self) -> None:
        """Should return empty list when no archive exists."""
        archived = self.runner.discover_archived()
        assert archived == []

    def test_discover_archived_with_migrations(self) -> None:
        """Should discover archived migrations."""
        archive_dir = self.migrations_dir / "archive"
        archive_dir.mkdir()

        (archive_dir / "0001_create_users.py").write_text("# migration")
        (archive_dir / "0002_add_email.py").write_text("# migration")

        archived = self.runner.discover_archived()
        assert len(archived) == 2
        assert archived[0].version == "0001"
        assert archived[0].name == "create_users"
        assert archived[1].version == "0002"
        assert archived[1].name == "add_email"

    def test_discover_ignores_archived_migrations(self) -> None:
        """discover() should not include archived migrations."""
        (self.migrations_dir / "0003_add_posts.py").write_text("# migration")
        (self.migrations_dir / "0004_add_comments.py").write_text("# migration")

        archive_dir = self.migrations_dir / "archive"
        archive_dir.mkdir()
        (archive_dir / "0001_create_users.py").write_text("# migration")
        (archive_dir / "0002_add_email.py").write_text("# migration")

        migrations = self.runner.discover()
        versions = [m.version for m in migrations]

        assert "0003" in versions
        assert "0004" in versions
        assert "0001" not in versions
        assert "0002" not in versions


class TestArchiveBoundaryError:
    """Tests for ArchiveBoundaryError exception."""

    def test_error_message_default(self) -> None:
        """Should have default error message."""
        error = ArchiveBoundaryError("0003")
        assert "0003" in str(error)
        assert "archive boundary" in str(error).lower()

    def test_error_message_custom(self) -> None:
        """Should accept custom error message."""
        error = ArchiveBoundaryError("0003", "Custom message")
        assert str(error) == "Custom message"
        assert error.boundary == "0003"


class TestCheckArchiveBoundaryHelper:
    """Tests for _check_archive_boundary helper function."""

    def test_check_no_boundary(self) -> None:
        """Should return None when no boundary exists."""
        from pykour.cli.commands.migrate import _check_archive_boundary

        def upgrade() -> None:
            op.create_table("users", op.column("id", "INTEGER", primary_key=True))

        migrations = [
            create_mock_migration("0001", "create_users", upgrade),
            create_mock_migration("0002", "add_email", upgrade),
        ]

        result = _check_archive_boundary(migrations, None)
        assert result is None

    def test_check_all_after_boundary(self) -> None:
        """Should return None when all migrations are after boundary."""
        from pykour.cli.commands.migrate import _check_archive_boundary

        def upgrade() -> None:
            op.create_table("users", op.column("id", "INTEGER", primary_key=True))

        migrations = [
            create_mock_migration("0004", "add_comments", upgrade),
            create_mock_migration("0005", "add_tags", upgrade),
        ]

        result = _check_archive_boundary(migrations, "0003")
        assert result is None

    def test_check_some_before_boundary(self) -> None:
        """Should return invalid migrations when some are at or before boundary."""
        from pykour.cli.commands.migrate import _check_archive_boundary

        def upgrade() -> None:
            op.create_table("users", op.column("id", "INTEGER", primary_key=True))

        migrations = [
            create_mock_migration("0002", "add_email", upgrade),
            create_mock_migration("0003", "add_posts", upgrade),
            create_mock_migration("0004", "add_comments", upgrade),
        ]

        result = _check_archive_boundary(migrations, "0003")
        assert result is not None
        assert len(result) == 2
        assert result[0].version == "0002"
        assert result[1].version == "0003"
