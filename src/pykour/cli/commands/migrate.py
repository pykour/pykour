"""Migrate command for database migrations."""

from __future__ import annotations

import argparse
import asyncio
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
        runner, db = await _get_runner(args)
        try:
            rolled_back = await runner.down(args.steps)
            if rolled_back:
                print(f"Rolled back {len(rolled_back)} migration(s):")
                for version in rolled_back:
                    print(f"  {version}")
            else:
                print("No migrations to rollback")
            return 0
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
