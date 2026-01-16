"""Migration code generator."""

from __future__ import annotations

import re
from pathlib import Path

from pykour.db.migrations.differ import (
    SchemaDiff,
    column_to_column_def,
    table_to_column_defs,
)
from pykour.db.migrations.operations import (
    AddColumn,
    CreateIndex,
    CreateTable,
    DropColumn,
    DropIndex,
    DropTable,
    Operation,
)


class MigrationGenerator:
    """Generates migration files from schema diffs."""

    def __init__(self, migrations_dir: Path) -> None:
        self._migrations_dir = migrations_dir

    def generate_from_diff(
        self,
        diff: SchemaDiff,
        message: str,
        driver: str = "sqlite",
    ) -> Path:
        """Generate a migration file from a schema diff.

        Args:
            diff: Schema differences to convert to migration.
            message: Migration message for the docstring.
            driver: Database driver name for type conversion.

        Returns:
            Path to the generated migration file.
        """
        version = self._next_version()
        filename = self._to_filename(version, message)
        path = self._migrations_dir / filename

        upgrade_ops: list[Operation] = []
        downgrade_ops: list[Operation] = []

        for table_cls in diff.tables_to_create:
            table_name = table_cls.get_tablename()
            columns = table_to_column_defs(table_cls, driver)
            upgrade_ops.append(CreateTable(table_name, columns))

            indexes = table_cls.get_indexes()
            for idx_name, idx in indexes.items():
                full_name = f"idx_{table_name}_{idx_name}"
                upgrade_ops.append(
                    CreateIndex(
                        full_name, table_name, idx.columns, idx.unique, where=idx.where
                    )
                )
                downgrade_ops.append(DropIndex(full_name))

            downgrade_ops.append(DropTable(table_name))

        for table_name in diff.tables_to_drop:
            upgrade_ops.append(DropTable(table_name))

        for table_name, col_name, col in diff.columns_to_add:
            col_def = column_to_column_def(col_name, col, driver)
            upgrade_ops.append(AddColumn(table_name, col_def))
            downgrade_ops.append(DropColumn(table_name, col_name))

        for table_name, col_name in diff.columns_to_drop:
            upgrade_ops.append(DropColumn(table_name, col_name))

        for table_name, idx_name, idx in diff.indexes_to_create:
            full_name = f"idx_{table_name}_{idx_name}"
            upgrade_ops.append(
                CreateIndex(
                    full_name, table_name, idx.columns, idx.unique, where=idx.where
                )
            )
            downgrade_ops.append(DropIndex(full_name))

        for table_name, idx_name in diff.indexes_to_drop:
            upgrade_ops.append(DropIndex(idx_name))

        downgrade_ops.reverse()

        content = self._generate_content(
            message,
            upgrade_ops,
            downgrade_ops,
        )

        path.write_text(content)
        return path

    def generate_empty(self, message: str) -> Path:
        """Generate an empty migration file.

        Args:
            message: Migration message for the docstring.

        Returns:
            Path to the generated migration file.
        """
        version = self._next_version()
        filename = self._to_filename(version, message)
        path = self._migrations_dir / filename

        content = self._generate_content(message, [], [])
        path.write_text(content)
        return path

    def _next_version(self) -> str:
        """Get the next migration version number."""
        existing = list(self._migrations_dir.glob("*.py"))
        if not existing:
            return "0001"

        versions = []
        for path in existing:
            match = re.match(r"^(\d{4})_", path.name)
            if match:
                versions.append(int(match.group(1)))

        if not versions:
            return "0001"

        return f"{max(versions) + 1:04d}"

    def _to_filename(self, version: str, message: str) -> str:
        """Convert version and message to filename."""
        slug = re.sub(r"[^a-z0-9]+", "_", message.lower()).strip("_")
        return f"{version}_{slug}.py"

    def _generate_content(
        self,
        message: str,
        upgrade_ops: list[Operation],
        downgrade_ops: list[Operation],
    ) -> str:
        """Generate migration file content."""
        lines = [
            f'"""{message}."""',
            "",
            "from pykour.db.migrations import op",
            "",
            "",
            "def upgrade():",
        ]

        if upgrade_ops:
            for op in upgrade_ops:
                code = op.to_code()
                for line in code.split("\n"):
                    lines.append(f"    {line}")
        else:
            lines.append("    pass")

        lines.extend(
            [
                "",
                "",
                "def downgrade():",
            ]
        )

        if downgrade_ops:
            for op in downgrade_ops:
                code = op.to_code()
                for line in code.split("\n"):
                    lines.append(f"    {line}")
        else:
            lines.append("    pass")

        lines.append("")

        return "\n".join(lines)
