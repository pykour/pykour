"""Migrate command for database migrations."""

from __future__ import annotations

import argparse
import asyncio
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pykour.db.migrations.table import Table


def register_command(subparsers: Any) -> None:
    """Register the migrate command and its subcommands."""
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Database migration commands",
    )
    migrate_parser.add_argument(
        "--database",
        "-d",
        type=str,
        default=None,
        help="Database URL (default: from PYKOUR_DATABASE_URL env)",
    )
    migrate_parser.add_argument(
        "--migrations-dir",
        "-m",
        type=str,
        default="migrations",
        help="Migrations directory (default: migrations)",
    )

    migrate_subparsers = migrate_parser.add_subparsers(
        dest="migrate_command",
        help="Migration commands",
    )

    init_parser = migrate_subparsers.add_parser("init", help="Initialize migrations")
    init_parser.set_defaults(func=cmd_init)

    new_parser = migrate_subparsers.add_parser("new", help="Create empty migration")
    new_parser.add_argument(
        "-m",
        "--message",
        required=True,
        help="Migration message",
    )
    new_parser.set_defaults(func=cmd_new)

    generate_parser = migrate_subparsers.add_parser(
        "generate",
        help="Generate migration from schema diff",
    )
    generate_parser.add_argument(
        "-m",
        "--message",
        required=True,
        help="Migration message",
    )
    generate_parser.add_argument(
        "--models",
        type=str,
        default="models",
        help="Models module path (default: models)",
    )
    generate_parser.set_defaults(func=cmd_generate)

    up_parser = migrate_subparsers.add_parser("up", help="Apply migrations")
    up_parser.add_argument(
        "steps",
        nargs="?",
        type=int,
        default=None,
        help="Number of migrations to apply (default: all)",
    )
    up_parser.set_defaults(func=cmd_up)

    down_parser = migrate_subparsers.add_parser("down", help="Rollback migrations")
    down_parser.add_argument(
        "steps",
        nargs="?",
        type=int,
        default=1,
        help="Number of migrations to rollback (default: 1)",
    )
    down_parser.set_defaults(func=cmd_down)

    status_parser = migrate_subparsers.add_parser(
        "status", help="Show migration status"
    )
    status_parser.set_defaults(func=cmd_status)

    history_parser = migrate_subparsers.add_parser(
        "history", help="Show migration history"
    )
    history_parser.set_defaults(func=cmd_history)

    squash_parser = migrate_subparsers.add_parser(
        "squash", help="Squash multiple migrations into one"
    )
    squash_parser.add_argument(
        "--from",
        "-f",
        dest="from_version",
        type=str,
        default=None,
        help="Start version (inclusive)",
    )
    squash_parser.add_argument(
        "--to",
        "-t",
        dest="to_version",
        type=str,
        default=None,
        help="End version (inclusive)",
    )
    squash_parser.add_argument(
        "--all",
        dest="squash_all",
        action="store_true",
        help="Squash all migrations",
    )
    squash_parser.add_argument(
        "-m",
        "--message",
        required=True,
        help="Squashed migration message",
    )
    squash_parser.add_argument(
        "--optimize",
        action="store_true",
        help="Optimize operations (merge redundant ops)",
    )
    squash_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be squashed without making changes",
    )
    squash_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip confirmation prompt",
    )
    squash_parser.set_defaults(func=cmd_squash)

    archive_parser = migrate_subparsers.add_parser(
        "archive",
        help="Archive migrations (freeze them, prevent rollback/squash)",
    )
    archive_parser.add_argument(
        "--to",
        "-t",
        dest="to_version",
        type=str,
        default=None,
        help="Archive all migrations up to this version (inclusive)",
    )
    archive_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be archived without making changes",
    )
    archive_parser.set_defaults(func=cmd_archive)

    migrate_parser.set_defaults(func=lambda args: migrate_parser.print_help() or 0)


def _get_database_url(args: argparse.Namespace) -> str:
    """Get database URL from args or environment."""
    import os

    url = args.database or os.environ.get("PYKOUR_DATABASE_URL")
    if not url:
        print("Error: Database URL required. Use --database or set PYKOUR_DATABASE_URL")
        raise SystemExit(1)
    return url


async def _get_runner(args: argparse.Namespace) -> Any:
    """Create and initialize migration runner.

    Returns:
        Tuple of (MigrationRunner, Database). Caller is responsible for
        calling db.disconnect() when done.

    Raises:
        Exception: Re-raises any exception after cleaning up the DB connection.
    """
    from pykour.db.database import Database
    from pykour.db.migrations.runner import MigrationRunner

    url = _get_database_url(args)
    db = Database(url)
    await db.connect()

    try:
        migrations_dir = Path(args.migrations_dir)
        runner = MigrationRunner(db, migrations_dir)
        await runner.init()
    except Exception:
        # Clean up DB connection on failure to prevent connection leak
        await db.disconnect()
        raise

    return runner, db


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize migrations."""

    async def run() -> int:
        from pykour.db.database import Database
        from pykour.db.migrations.runner import MigrationRunner

        migrations_dir = Path(args.migrations_dir)

        if args.database:
            url = _get_database_url(args)
            db = Database(url)
            await db.connect()
            runner = MigrationRunner(db, migrations_dir)
            await runner.init()
            await db.disconnect()
            print(f"Initialized migrations in {migrations_dir}")
            print("Created migrations table in database")
        else:
            migrations_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created migrations directory: {migrations_dir}")
            print("Note: Run with --database to also create the migrations table")

        return 0

    return asyncio.run(run())


def cmd_new(args: argparse.Namespace) -> int:
    """Create a new empty migration."""

    async def run() -> int:
        from pykour.db.migrations.generator import MigrationGenerator

        migrations_dir = Path(args.migrations_dir)
        migrations_dir.mkdir(parents=True, exist_ok=True)

        generator = MigrationGenerator(migrations_dir)
        path = generator.generate_empty(args.message)

        print(f"Created migration: {path}")
        return 0

    return asyncio.run(run())


def cmd_generate(args: argparse.Namespace) -> int:
    """Generate migration from schema diff."""

    async def run() -> int:
        from pykour.db.migrations.generator import MigrationGenerator

        runner, db = await _get_runner(args)

        try:
            from pykour.db.migrations.differ import SchemaDiffer
            from pykour.db.migrations.introspector import get_introspector

            tables = _load_tables(args.models)

            if not tables:
                print(f"No Table classes found in {args.models}")
                return 1

            introspector = get_introspector(db._driver)
            differ = SchemaDiffer(introspector)

            conn = await db._driver.acquire()
            try:
                diff = await differ.diff(conn, tables)
            finally:
                await db._driver.release(conn)

            if diff.is_empty():
                print("No schema changes detected")
                return 0

            migrations_dir = Path(args.migrations_dir)
            generator = MigrationGenerator(migrations_dir)
            path = generator.generate_from_diff(diff, args.message)

            print(f"Generated migration: {path}")
            print(f"  Tables to create: {len(diff.tables_to_create)}")
            print(f"  Tables to drop: {len(diff.tables_to_drop)}")
            print(f"  Columns to add: {len(diff.columns_to_add)}")
            print(f"  Columns to drop: {len(diff.columns_to_drop)}")

            return 0
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _load_tables(models_path: str) -> list[type[Table]]:
    """Load Table classes from a module."""
    import importlib
    import sys

    from pykour.db.migrations.table import Table

    # Only add "." to sys.path if not already present
    added_cwd = False
    if "." not in sys.path:
        sys.path.insert(0, ".")
        added_cwd = True

    try:
        try:
            module = importlib.import_module(models_path)
        except ImportError as e:
            print(f"Error importing {models_path}: {e}")
            return []

        tables = []
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, Table) and obj is not Table:
                tables.append(obj)

        return tables
    finally:
        # Clean up sys.path to avoid polluting the import path
        if added_cwd:
            sys.path.remove(".")


def cmd_up(args: argparse.Namespace) -> int:
    """Apply pending migrations."""

    async def run() -> int:
        runner, db = await _get_runner(args)
        try:
            applied = await runner.up(args.steps)
            if applied:
                print(f"Applied {len(applied)} migration(s):")
                for version in applied:
                    print(f"  {version}")
            else:
                print("No pending migrations")
            return 0
        finally:
            await db.disconnect()

    return asyncio.run(run())


def cmd_down(args: argparse.Namespace) -> int:
    """Rollback migrations."""

    async def run() -> int:
        from pykour.db.migrations.exceptions import ArchiveBoundaryError

        runner, db = await _get_runner(args)
        try:
            boundary = runner.get_archive_boundary()
            if boundary:
                applied = await runner.get_applied()
                to_rollback = list(reversed(applied))[: args.steps]

                invalid = [m for m in to_rollback if m.version <= boundary]
                if invalid:
                    valid_count = len(to_rollback) - len(invalid)
                    if valid_count > 0:
                        rolled_back = await runner.down(valid_count)
                        print(f"Rolled back {len(rolled_back)} migration(s):")
                        for version in rolled_back:
                            print(f"  {version}")
                        print(
                            f"\nStopped at archive boundary ({boundary}). "
                            f"Cannot rollback archived migrations."
                        )
                    else:
                        print(
                            f"Error: Cannot rollback past archive boundary ({boundary})"
                        )
                    return 1

            rolled_back = await runner.down(args.steps)
            if rolled_back:
                print(f"Rolled back {len(rolled_back)} migration(s):")
                for version in rolled_back:
                    print(f"  {version}")
            else:
                print("No migrations to rollback")
            return 0
        except ArchiveBoundaryError as e:
            print(f"Error: {e}")
            return 1
        finally:
            await db.disconnect()

    return asyncio.run(run())


def cmd_status(args: argparse.Namespace) -> int:
    """Show migration status."""

    async def run() -> int:
        runner, db = await _get_runner(args)
        try:
            status = await runner.status()

            print(f"Current version: {status['current_version'] or 'None'}")
            print(f"Total migrations: {status['total_migrations']}")
            print(f"Applied: {status['applied_count']}")
            print(f"Pending: {status['pending_count']}")

            if status["pending"]:
                print("\nPending migrations:")
                for m in status["pending"]:
                    print(f"  {m['version']} - {m['name']}")

            return 0
        finally:
            await db.disconnect()

    return asyncio.run(run())


def cmd_history(args: argparse.Namespace) -> int:
    """Show migration history."""

    async def run() -> int:
        runner, db = await _get_runner(args)
        try:
            history = await runner.history()

            if history:
                print("Migration history:")
                for m in history:
                    print(f"  {m['version']} - {m['name']} ({m['applied_at']})")
            else:
                print("No migrations applied yet")

            return 0
        finally:
            await db.disconnect()

    return asyncio.run(run())


def cmd_squash(args: argparse.Namespace) -> int:
    """Squash multiple migrations into one."""

    async def run() -> int:
        migrations_dir = Path(args.migrations_dir)

        if not migrations_dir.exists():
            print(f"Migrations directory not found: {migrations_dir}")
            return 1

        if args.database:
            runner, db = await _get_runner(args)
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

    class DummyDb:
        """Dummy database for file-only mode."""

        _driver = None

    dummy_db = DummyDb()
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

        class DummyDb:
            """Dummy database for file-only mode."""

            _driver = None

        runner = MigrationRunner(DummyDb(), migrations_dir)  # type: ignore[arg-type]
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
