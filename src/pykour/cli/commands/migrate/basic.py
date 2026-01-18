"""Basic migration commands: init, new, generate, up, down."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from pykour.cli.commands.migrate.utils import get_database_url, get_runner, load_tables


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize migrations."""

    async def run() -> int:
        from pykour.db.database import Database
        from pykour.db.migrations.runner import MigrationRunner

        migrations_dir = Path(args.migrations_dir)

        if args.database:
            url = get_database_url(args)
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

        runner, db = await get_runner(args)

        try:
            from pykour.db.migrations.differ import SchemaDiffer
            from pykour.db.migrations.introspector import get_introspector

            tables = load_tables(args.models)

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


def cmd_up(args: argparse.Namespace) -> int:
    """Apply pending migrations."""

    async def run() -> int:
        runner, db = await get_runner(args)
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

        runner, db = await get_runner(args)
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
