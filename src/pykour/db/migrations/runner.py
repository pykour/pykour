"""Migration runner."""

from __future__ import annotations

import importlib.util
import re
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable

from pykour.db.migrations.exceptions import (
    InvalidMigrationError,
    MigrationAlreadyAppliedError,
    MigrationNotAppliedError,
    OperationError,
)
from pykour.db.migrations.op import OpContext, set_context
from pykour.db.migrations.version import VersionManager

if TYPE_CHECKING:
    from pykour.db.database import Database

MIGRATION_PATTERN = re.compile(r"^(\d{4})_(.+)\.py$")


@dataclass
class Migration:
    """A migration file representation."""

    version: str
    name: str
    path: Path
    module: ModuleType | None = None

    @property
    def full_name(self) -> str:
        """Get the full migration name (version_name)."""
        return f"{self.version}_{self.name}"

    def load(self) -> None:
        """Load the migration module."""
        if self.module is not None:
            return

        spec = importlib.util.spec_from_file_location(self.full_name, self.path)
        if spec is None or spec.loader is None:
            raise InvalidMigrationError(str(self.path), "Cannot load module")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.module = module

    def get_upgrade(self) -> Callable[[], None]:
        """Get the upgrade function."""
        if self.module is None:
            self.load()
        func = getattr(self.module, "upgrade", None)
        if func is None:
            raise InvalidMigrationError(str(self.path), "Missing upgrade() function")
        return func

    def get_downgrade(self) -> Callable[[], None]:
        """Get the downgrade function."""
        if self.module is None:
            self.load()
        func = getattr(self.module, "downgrade", None)
        if func is None:
            raise InvalidMigrationError(str(self.path), "Missing downgrade() function")
        return func


class MigrationRunner:
    """Runs database migrations."""

    def __init__(
        self,
        db: Database,
        migrations_dir: Path | str,
    ) -> None:
        """Initialize the migration runner.

        Args:
            db: Database instance.
            migrations_dir: Path to the migrations directory.
        """
        self._db = db
        self._migrations_dir = Path(migrations_dir)
        self._version_manager = VersionManager(db._driver)

    async def init(self) -> None:
        """Initialize the migrations system.

        Creates the migrations table and directory if needed.
        """
        self._migrations_dir.mkdir(parents=True, exist_ok=True)

        conn = await self._db._driver.acquire()
        try:
            await self._version_manager.init(conn)
        finally:
            await self._db._driver.release(conn)

    def discover(self) -> list[Migration]:
        """Discover all migration files.

        Returns:
            List of migrations sorted by version.
        """
        migrations: list[Migration] = []

        if not self._migrations_dir.exists():
            return migrations

        for path in sorted(self._migrations_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue

            match = MIGRATION_PATTERN.match(path.name)
            if match:
                version = match.group(1)
                name = match.group(2)
                migrations.append(Migration(version=version, name=name, path=path))

        return migrations

    async def get_pending(self) -> list[Migration]:
        """Get pending (not yet applied) migrations.

        Returns:
            List of pending migrations sorted by version.
        """
        all_migrations = self.discover()
        conn = await self._db._driver.acquire()
        try:
            applied = await self._version_manager.get_applied_versions(conn)
        finally:
            await self._db._driver.release(conn)

        return [m for m in all_migrations if m.version not in applied]

    async def get_applied(self) -> list[Migration]:
        """Get applied migrations.

        Returns:
            List of applied migrations sorted by version.
        """
        all_migrations = self.discover()
        conn = await self._db._driver.acquire()
        try:
            applied = await self._version_manager.get_applied_versions(conn)
        finally:
            await self._db._driver.release(conn)

        return [m for m in all_migrations if m.version in applied]

    async def up(self, steps: int | None = None) -> list[str]:
        """Apply pending migrations.

        Args:
            steps: Number of migrations to apply. None means all.

        Returns:
            List of applied migration versions.
        """
        pending = await self.get_pending()

        if steps is not None:
            pending = pending[:steps]

        applied: list[str] = []

        for migration in pending:
            await self._run_upgrade(migration)
            applied.append(migration.version)

        return applied

    async def down(self, steps: int = 1) -> list[str]:
        """Rollback applied migrations.

        Args:
            steps: Number of migrations to rollback.

        Returns:
            List of rolled back migration versions.
        """
        applied = await self.get_applied()
        to_rollback = list(reversed(applied))[:steps]

        rolled_back: list[str] = []

        for migration in to_rollback:
            await self._run_downgrade(migration)
            rolled_back.append(migration.version)

        return rolled_back

    async def _run_upgrade(self, migration: Migration) -> None:
        """Run a single upgrade migration."""
        conn = await self._db._driver.acquire()
        try:
            if await self._version_manager.is_applied(conn, migration.version):
                raise MigrationAlreadyAppliedError(migration.version)

            migration.load()
            upgrade_func = migration.get_upgrade()

            await self._db._driver.begin(conn)
            try:
                ctx = OpContext(driver=self._db._driver, conn=conn, operations=[])
                set_context(ctx)

                upgrade_func()

                for op in ctx.operations:
                    await op.execute(self._db._driver, conn)

                set_context(None)

                await self._version_manager.mark_applied(
                    conn, migration.version, migration.name
                )
                await self._db._driver.commit(conn)
            except Exception as e:
                set_context(None)
                await self._db._driver.rollback(conn)
                raise OperationError(
                    f"Migration {migration.version} failed: {e}"
                ) from e
        finally:
            await self._db._driver.release(conn)

    async def _run_downgrade(self, migration: Migration) -> None:
        """Run a single downgrade migration."""
        conn = await self._db._driver.acquire()
        try:
            if not await self._version_manager.is_applied(conn, migration.version):
                raise MigrationNotAppliedError(migration.version)

            migration.load()
            downgrade_func = migration.get_downgrade()

            await self._db._driver.begin(conn)
            try:
                ctx = OpContext(driver=self._db._driver, conn=conn, operations=[])
                set_context(ctx)

                downgrade_func()

                for op in ctx.operations:
                    await op.execute(self._db._driver, conn)

                set_context(None)

                await self._version_manager.mark_unapplied(conn, migration.version)
                await self._db._driver.commit(conn)
            except Exception as e:
                set_context(None)
                await self._db._driver.rollback(conn)
                raise OperationError(f"Rollback {migration.version} failed: {e}") from e
        finally:
            await self._db._driver.release(conn)

    async def status(self) -> dict[str, Any]:
        """Get migration status.

        Returns:
            Dict with current status information.
        """
        all_migrations = self.discover()
        conn = await self._db._driver.acquire()
        try:
            applied_records = await self._version_manager.get_applied(conn)
            current = await self._version_manager.get_current_version(conn)
        finally:
            await self._db._driver.release(conn)

        applied_versions = {r.version for r in applied_records}
        pending = [m for m in all_migrations if m.version not in applied_versions]

        return {
            "current_version": current,
            "total_migrations": len(all_migrations),
            "applied_count": len(applied_records),
            "pending_count": len(pending),
            "pending": [{"version": m.version, "name": m.name} for m in pending],
            "applied": [
                {
                    "version": r.version,
                    "name": r.name,
                    "applied_at": r.applied_at.isoformat(),
                }
                for r in applied_records
            ],
        }

    async def history(self) -> list[dict[str, Any]]:
        """Get migration history.

        Returns:
            List of applied migrations with timestamps.
        """
        conn = await self._db._driver.acquire()
        try:
            records = await self._version_manager.get_applied(conn)
        finally:
            await self._db._driver.release(conn)

        return [
            {
                "version": r.version,
                "name": r.name,
                "applied_at": r.applied_at.isoformat(),
            }
            for r in records
        ]
