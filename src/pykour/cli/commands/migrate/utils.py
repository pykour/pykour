"""Utility functions for migrate commands."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pykour.db.database import Database
    from pykour.db.migrations.runner import MigrationRunner
    from pykour.db.migrations.table import Table


def get_database_url(args: argparse.Namespace) -> str:
    """Get database URL from args or environment."""
    import os

    url = args.database or os.environ.get("PYKOUR_DATABASE_URL")
    if not url:
        print("Error: Database URL required. Use --database or set PYKOUR_DATABASE_URL")
        raise SystemExit(1)
    return url


async def get_runner(
    args: argparse.Namespace,
) -> tuple["MigrationRunner", "Database"]:
    """Create and initialize migration runner.

    Returns:
        Tuple of (MigrationRunner, Database). Caller is responsible for
        calling db.disconnect() when done.

    Raises:
        Exception: Re-raises any exception after cleaning up the DB connection.
    """
    from pykour.db.database import Database
    from pykour.db.migrations.runner import MigrationRunner

    url = get_database_url(args)
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


def load_tables(models_path: str) -> list[type["Table"]]:
    """Load Table classes from a module."""
    import importlib

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
