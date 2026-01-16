"""Migration analyzer module."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

from pykour.db.migrations.op import OpContext, set_context
from pykour.db.migrations.operations import (
    AddColumn,
    AlterColumn,
    CreateIndex,
    CreateTable,
    DropColumn,
    DropIndex,
    DropTable,
    RenameColumn,
    RenameTable,
)

if TYPE_CHECKING:
    from pykour.db.migrations.runner import Migration


class MigrationAnalyzer:
    """Analyzes migrations to extract table information."""

    def analyze(self, migration: Migration) -> set[str]:
        """Extract table names that a migration affects.

        Args:
            migration: Migration to analyze.

        Returns:
            Set of table names affected by the migration.
        """
        migration.load()
        upgrade_func = migration.get_upgrade()

        operations = self._run_migration_func(upgrade_func)

        tables: set[str] = set()
        for op in operations:
            tables.update(self._get_tables_from_operation(op))

        return tables

    def group_by_table(self, migrations: list[Migration]) -> dict[str, list[Migration]]:
        """Group migrations by the tables they affect.

        Migrations affecting multiple tables are grouped under "multiple tables".

        Args:
            migrations: List of migrations to group.

        Returns:
            Dict mapping table names to lists of migrations.
        """
        groups: dict[str, list[Migration]] = defaultdict(list)

        for migration in migrations:
            tables = self.analyze(migration)

            if len(tables) == 0:
                groups["(no tables)"].append(migration)
            elif len(tables) == 1:
                table_name = next(iter(tables))
                groups[table_name].append(migration)
            else:
                groups["multiple tables"].append(migration)

        sorted_groups: dict[str, list[Migration]] = {}
        for key in sorted(groups.keys()):
            sorted_groups[key] = sorted(groups[key], key=lambda m: m.version)

        return sorted_groups

    def get_table_info(self, migration: Migration) -> str:
        """Get a string describing the tables affected by a migration.

        Args:
            migration: Migration to analyze.

        Returns:
            String describing affected tables.
        """
        tables = self.analyze(migration)

        if len(tables) == 0:
            return "(no tables)"
        elif len(tables) == 1:
            return next(iter(tables))
        else:
            return ", ".join(sorted(tables))

    def _run_migration_func(self, func: Any) -> list[Any]:
        """Run a migration function and collect its operations.

        Args:
            func: The upgrade or downgrade function.

        Returns:
            List of operations.
        """
        ctx = OpContext(driver=None, conn=None, operations=[])  # type: ignore[arg-type]
        set_context(ctx)
        try:
            func()
            return ctx.operations.copy()
        finally:
            set_context(None)

    def _get_tables_from_operation(self, op: Any) -> set[str]:
        """Extract table names from an operation.

        Args:
            op: Operation to extract tables from.

        Returns:
            Set of table names.
        """
        tables: set[str] = set()

        if isinstance(op, CreateTable):
            tables.add(op.name)
        elif isinstance(op, DropTable):
            tables.add(op.name)
        elif isinstance(op, AddColumn):
            tables.add(op.table)
        elif isinstance(op, DropColumn):
            tables.add(op.table)
        elif isinstance(op, AlterColumn):
            tables.add(op.table)
        elif isinstance(op, RenameTable):
            tables.add(op.old_name)
            tables.add(op.new_name)
        elif isinstance(op, RenameColumn):
            tables.add(op.table)
        elif isinstance(op, CreateIndex):
            tables.add(op.table)
        elif isinstance(op, DropIndex):
            pass

        return tables
