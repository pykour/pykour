"""Migration squasher module."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pykour.db.migrations.exceptions import SquashRangeError
from pykour.db.migrations.op import OpContext, set_context
from pykour.db.migrations.operations import Operation

if TYPE_CHECKING:
    from pykour.db.migrations.runner import Migration


@dataclass
class SquashResult:
    """Result of a squash operation."""

    path: Path
    version: str
    name: str
    content: str
    upgrade_ops: list[Operation]
    downgrade_ops: list[Operation]
    original_versions: list[str]


class MigrationSquasher:
    """Squashes multiple migrations into a single migration file."""

    def __init__(self, migrations_dir: Path) -> None:
        """Initialize the squasher.

        Args:
            migrations_dir: Path to the migrations directory.
        """
        self._migrations_dir = migrations_dir

    def squash(
        self,
        migrations: list[Migration],
        message: str,
        optimize: bool = False,
    ) -> SquashResult:
        """Squash multiple migrations into one.

        Args:
            migrations: List of migrations to squash (must be at least 2).
            message: Message for the squashed migration.
            optimize: Whether to optimize operations.

        Returns:
            SquashResult with the generated migration details.

        Raises:
            SquashRangeError: If fewer than 2 migrations are provided.
        """
        if len(migrations) < 2:
            raise SquashRangeError(
                f"Need at least 2 migrations to squash. Found: {len(migrations)}"
            )

        sorted_migrations = sorted(migrations, key=lambda m: m.version)

        all_upgrade_ops: list[Operation] = []
        all_downgrade_ops: list[Operation] = []
        original_versions: list[str] = []

        for migration in sorted_migrations:
            upgrade_ops, downgrade_ops = self._extract_operations(migration)
            all_upgrade_ops.extend(upgrade_ops)
            all_downgrade_ops.extend(downgrade_ops)
            original_versions.append(migration.version)

        all_downgrade_ops.reverse()

        if optimize:
            from pykour.db.migrations.optimizer import OperationOptimizer

            optimizer = OperationOptimizer()
            all_upgrade_ops = optimizer.optimize(all_upgrade_ops)
            all_downgrade_ops = [op.reverse() for op in reversed(all_upgrade_ops)]

        version = self._next_version()
        filename = self._to_filename(version, message)
        path = self._migrations_dir / filename

        content = self._generate_squashed_content(
            message,
            all_upgrade_ops,
            all_downgrade_ops,
            original_versions,
        )

        path.write_text(content)

        return SquashResult(
            path=path,
            version=version,
            name=message,
            content=content,
            upgrade_ops=all_upgrade_ops,
            downgrade_ops=all_downgrade_ops,
            original_versions=original_versions,
        )

    def _extract_operations(
        self, migration: Migration
    ) -> tuple[list[Operation], list[Operation]]:
        """Extract upgrade and downgrade operations from a migration.

        Args:
            migration: Migration to extract operations from.

        Returns:
            Tuple of (upgrade_ops, downgrade_ops).
        """
        migration.load()

        upgrade_ops = self._run_migration_func(migration.get_upgrade())
        downgrade_ops = self._run_migration_func(migration.get_downgrade())

        return upgrade_ops, downgrade_ops

    def _run_migration_func(self, func: Any) -> list[Operation]:
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

    def _generate_squashed_content(
        self,
        message: str,
        upgrade_ops: list[Operation],
        downgrade_ops: list[Operation],
        original_versions: list[str],
    ) -> str:
        """Generate the squashed migration file content.

        Args:
            message: Migration message.
            upgrade_ops: List of upgrade operations.
            downgrade_ops: List of downgrade operations.
            original_versions: List of original migration versions.

        Returns:
            Migration file content as string.
        """
        versions_str = ", ".join(original_versions)
        lines = [
            f'"""{message}.',
            "",
            f"Squashed from migrations: {versions_str}",
            '"""',
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
