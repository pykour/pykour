"""Maintenance commands: squash, archive."""

from __future__ import annotations

import argparse
import asyncio
import shutil
from pathlib import Path
from typing import Any

from pykour.cli.commands.migrate.utils import get_runner


class _DummyDb:
    """Dummy database for file-only mode operations."""

    _driver = None


def cmd_squash(args: argparse.Namespace) -> int:
    """Squash multiple migrations into one."""

    async def run() -> int:
        migrations_dir = Path(args.migrations_dir)

        if not migrations_dir.exists():
            print(f"Migrations directory not found: {migrations_dir}")
            return 1

        if args.database:
            runner, db = await get_runner(args)
            try:
                return await _run_squash(args, runner, db, migrations_dir)
            finally:
                await db.disconnect()
        else:
            return await _run_squash_without_db(args, migrations_dir)

    return asyncio.run(run())


async def _run_squash(
    args: argparse.Namespace,
    runner: Any,
    db: Any,
    migrations_dir: Path,
) -> int:
    """Run squash with database connection."""
    from pykour.db.migrations.squasher import MigrationSquasher

    all_migrations = runner.discover()

    if not all_migrations:
        print("No migrations found")
        return 1

    conn = await db._driver.acquire()
    try:
        applied_versions = await runner._version_manager.get_applied_versions(conn)
    finally:
        await db._driver.release(conn)

    selected = await _select_migrations_for_squash(
        args, all_migrations, applied_versions
    )

    if not selected:
        print("No migrations selected for squash")
        return 0

    if len(selected) < 2:
        print("Need at least 2 migrations to squash")
        return 1

    boundary = runner.get_archive_boundary()
    invalid = _check_archive_boundary(selected, boundary)
    if invalid:
        print("Error: Cannot squash archived migrations:")
        for m in invalid:
            print(f"  {m.version}_{m.name}")
        print(f"Archive boundary: {boundary}")
        print("Only migrations after the archive boundary can be squashed.")
        return 1

    pending_versions = [
        m.version for m in selected if m.version not in applied_versions
    ]

    if not args.yes:
        from pykour.cli.interactive import confirm_squash

        if not confirm_squash(selected, pending_versions):
            print("Squash cancelled")
            return 0

    if args.dry_run:
        _print_dry_run(selected, pending_versions, args.message, args.optimize)
        return 0

    squasher = MigrationSquasher(migrations_dir)
    result = squasher.squash(selected, args.message, optimize=args.optimize)

    print(f"Created: {result.path}")
    print(f"  Upgrade operations: {len(result.upgrade_ops)}")
    print(f"  Downgrade operations: {len(result.downgrade_ops)}")
    print(f"  Original migrations: {', '.join(result.original_versions)}")

    applied_selected = [m for m in selected if m.version in applied_versions]
    if applied_selected:
        conn = await db._driver.acquire()
        try:
            await runner._version_manager.replace_versions(
                conn,
                [m.version for m in applied_selected],
                result.version,
                args.message,
            )
        finally:
            await db._driver.release(conn)
        print(f"Updated migration history (replaced {len(applied_selected)} records)")

    print(
        "\nNote: Original migration files are preserved. Delete them manually after verifying."
    )

    return 0


async def _run_squash_without_db(
    args: argparse.Namespace,
    migrations_dir: Path,
) -> int:
    """Run squash without database connection (file-only mode)."""
    from pykour.db.migrations.runner import MigrationRunner
    from pykour.db.migrations.squasher import MigrationSquasher

    dummy_db = _DummyDb()
    runner = MigrationRunner(dummy_db, migrations_dir)  # type: ignore[arg-type]

    all_migrations = runner.discover()

    if not all_migrations:
        print("No migrations found")
        return 1

    selected = await _select_migrations_for_squash(args, all_migrations, set())

    if not selected:
        print("No migrations selected for squash")
        return 0

    if len(selected) < 2:
        print("Need at least 2 migrations to squash")
        return 1

    boundary = runner.get_archive_boundary()
    invalid = _check_archive_boundary(selected, boundary)
    if invalid:
        print("Error: Cannot squash archived migrations:")
        for m in invalid:
            print(f"  {m.version}_{m.name}")
        print(f"Archive boundary: {boundary}")
        print("Only migrations after the archive boundary can be squashed.")
        return 1

    if not args.yes:
        from pykour.cli.interactive import confirm_squash

        if not confirm_squash(selected, [m.version for m in selected]):
            print("Squash cancelled")
            return 0

    if args.dry_run:
        _print_dry_run(
            selected, [m.version for m in selected], args.message, args.optimize
        )
        return 0

    squasher = MigrationSquasher(migrations_dir)
    result = squasher.squash(selected, args.message, optimize=args.optimize)

    print(f"Created: {result.path}")
    print(f"  Upgrade operations: {len(result.upgrade_ops)}")
    print(f"  Downgrade operations: {len(result.downgrade_ops)}")
    print(f"  Original migrations: {', '.join(result.original_versions)}")
    print(
        "\nNote: Original migration files are preserved. Delete them manually after verifying."
    )
    print("Note: Run with --database to also update the migration history.")

    return 0


async def _select_migrations_for_squash(
    args: argparse.Namespace,
    all_migrations: list[Any],
    applied_versions: set[str],
) -> list[Any]:
    """Select migrations to squash based on args or interactive mode."""
    from pykour.db.migrations.analyzer import MigrationAnalyzer

    if args.squash_all:
        return all_migrations

    if args.from_version or args.to_version:
        return _filter_migrations_by_range(
            all_migrations, args.from_version, args.to_version
        )

    analyzer = MigrationAnalyzer()
    groups = analyzer.group_by_table(all_migrations)

    from pykour.cli.interactive import select_migrations

    return select_migrations(all_migrations, groups, applied_versions)


def _filter_migrations_by_range(
    migrations: list[Any],
    from_version: str | None,
    to_version: str | None,
) -> list[Any]:
    """Filter migrations by version range."""
    result = []
    for m in migrations:
        if from_version and m.version < from_version:
            continue
        if to_version and m.version > to_version:
            continue
        result.append(m)
    return result


def _print_dry_run(
    migrations: list[Any],
    pending_versions: list[str],
    message: str,
    optimize: bool,
) -> None:
    """Print dry run information."""
    print("[DRY RUN] Would squash the following migrations:")
    for m in migrations:
        status = "(pending)" if m.version in pending_versions else "(applied)"
        print(f"  {m.version}_{m.name} {status}")

    print(f"\nWould create migration with message: {message}")
    if optimize:
        print("Operations would be optimized")
    print("\nNo changes made.")


def cmd_archive(args: argparse.Namespace) -> int:
    """Archive migrations (freeze them, prevent rollback/squash)."""

    async def run() -> int:
        from pykour.db.migrations.runner import MigrationRunner

        migrations_dir = Path(args.migrations_dir)

        if not migrations_dir.exists():
            print(f"Migrations directory not found: {migrations_dir}")
            return 1

        runner = MigrationRunner(_DummyDb(), migrations_dir)  # type: ignore[arg-type]
        all_migrations = runner.discover()

        if not all_migrations:
            print("No migrations found")
            return 1

        current_boundary = runner.get_archive_boundary()

        if args.to_version:
            targets = [m for m in all_migrations if m.version <= args.to_version]
            if current_boundary:
                targets = [m for m in targets if m.version > current_boundary]
        else:
            from pykour.cli.interactive import select_archive_target

            targets = select_archive_target(all_migrations, current_boundary)

        if not targets:
            print("No migrations to archive")
            return 0

        archive_dir = migrations_dir / "archive"

        if args.dry_run:
            print("[DRY RUN] Would archive the following migrations:")
            for m in targets:
                print(f"  {m.full_name}")
            print(f"\nWould move {len(targets)} file(s) to {archive_dir}")
            print("No changes made.")
            return 0

        archive_dir.mkdir(exist_ok=True)

        for m in targets:
            src = m.path
            dst = archive_dir / m.path.name
            shutil.move(str(src), str(dst))
            print(f"Archived: {m.full_name}")

        new_boundary = max(m.version for m in targets)
        print(f"\nArchive boundary is now: {new_boundary}")
        print("Archived migrations cannot be rolled back or squashed.")

        return 0

    return asyncio.run(run())


def _check_archive_boundary(
    migrations: list[Any],
    boundary: str | None,
) -> list[Any] | None:
    """Check if any migrations are at or before the archive boundary.

    Returns:
        List of invalid migrations if any are at or before boundary, None otherwise.
    """
    if not boundary:
        return None

    invalid = [m for m in migrations if m.version <= boundary]
    return invalid if invalid else None
