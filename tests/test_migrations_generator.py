"""Tests for migration generator."""

from pathlib import Path


from pykour.db.migrations.differ import SchemaDiff
from pykour.db.migrations.generator import MigrationGenerator
from pykour.db.migrations.table import Column, IndexDef, Table
from pykour.db.migrations.types import Integer, String


class TestMigrationGenerator:
    """Tests for MigrationGenerator class."""

    def test_generate_empty(self, tmp_path: Path) -> None:
        """Generate empty migration should create file."""
        generator = MigrationGenerator(tmp_path)
        path = generator.generate_empty("add custom index")

        assert path.exists()
        assert path.name == "0001_add_custom_index.py"

        content = path.read_text()
        assert '"""add custom index."""' in content
        assert "def upgrade():" in content
        assert "def downgrade():" in content

    def test_generate_increments_version(self, tmp_path: Path) -> None:
        """Version should increment with each migration."""
        generator = MigrationGenerator(tmp_path)

        path1 = generator.generate_empty("first")
        path2 = generator.generate_empty("second")

        assert "0001_" in path1.name
        assert "0002_" in path2.name

    def test_generate_from_diff_create_table(self, tmp_path: Path) -> None:
        """Generate from diff should create migration for new table."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True, autoincrement=True)
            name = Column(String(100), nullable=False)

        diff = SchemaDiff(tables_to_create=[UserTable])

        generator = MigrationGenerator(tmp_path)
        path = generator.generate_from_diff(diff, "create users table")

        assert path.exists()
        content = path.read_text()

        assert "op.create_table" in content
        assert '"users"' in content
        assert '"id"' in content
        assert '"name"' in content
        assert "op.drop_table" in content

    def test_filename_slug(self, tmp_path: Path) -> None:
        """Filename should convert message to slug."""
        generator = MigrationGenerator(tmp_path)
        path = generator.generate_empty("Add User Email Index!")

        assert "add_user_email_index" in path.name

    def test_generate_from_diff_create_table_with_meta(self, tmp_path: Path) -> None:
        """Generate from diff should create migration with indexes from Meta."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True, autoincrement=True)
            email = Column(String(255), nullable=False)
            domain = Column(String(100))

            class Meta:
                unique_together = [("email", "domain")]
                search_keys = [["email"]]

        diff = SchemaDiff(tables_to_create=[UserTable])

        generator = MigrationGenerator(tmp_path)
        path = generator.generate_from_diff(diff, "create users with indexes")

        assert path.exists()
        content = path.read_text()

        assert "op.create_table" in content
        assert "op.create_index" in content
        assert "uq_users_email_domain" in content
        assert "idx_users_email" in content
        assert "unique=True" in content
        assert "op.drop_index" in content

    def test_generate_from_diff_add_index(self, tmp_path: Path) -> None:
        """Generate from diff should create migration for new index."""
        idx_def = IndexDef(
            name="uq_users_email",
            table="users",
            columns=["email"],
            unique=True,
        )

        diff = SchemaDiff(indexes_to_create=[("users", idx_def)])

        generator = MigrationGenerator(tmp_path)
        path = generator.generate_from_diff(diff, "add email index")

        assert path.exists()
        content = path.read_text()

        assert "op.create_index" in content
        assert "uq_users_email" in content
        assert "unique=True" in content
        assert "op.drop_index" in content

    def test_generate_from_diff_drop_index(self, tmp_path: Path) -> None:
        """Generate from diff should create migration to drop index."""
        diff = SchemaDiff(indexes_to_drop=[("users", "idx_users_old")])

        generator = MigrationGenerator(tmp_path)
        path = generator.generate_from_diff(diff, "drop old index")

        assert path.exists()
        content = path.read_text()

        assert "op.drop_index" in content
        assert "idx_users_old" in content
