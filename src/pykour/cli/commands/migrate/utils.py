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
    """Get database URL following the standard priority order.

    Priority (highest to lowest):
    1. CLI flag (--database)
    2. Environment variable (PYKOUR_DATABASE_URL)
    3. pykour.toml database.url (with ${VAR} expansion)

    Args:
        args: Parsed CLI arguments

    Returns:
        Database URL string

    Raises:
        SystemExit: If no database URL is configured
    """
    from pykour.config.cli import get_database_url_from_config

    url = get_database_url_from_config(args)
    if not url:
        print(
            "Error: Database URL required.\n"
            "Configure it via:\n"
            "  - --database flag\n"
            "  - PYKOUR_DATABASE_URL environment variable\n"
            "  - database.url in pykour.toml"
        )
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
    """Load Table classes from a module or package.

    Recursively scans the module and all submodules for Table subclasses.

    Args:
        models_path: Module path (e.g., "app.models" or "models")

    Returns:
        List of Table subclasses found in the module(s).
    """
    import importlib
    import inspect
    import pkgutil

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

        tables: list[type[Table]] = []
        seen: set[type] = set()

        def collect_tables_from_module(mod: object) -> None:
            """Collect Table subclasses from a module."""
            for name, obj in inspect.getmembers(mod, inspect.isclass):
                if (
                    obj not in seen
                    and obj is not Table
                    and issubclass(obj, Table)
                    and hasattr(obj, "__tablename__")
                ):
                    seen.add(obj)
                    tables.append(obj)

        # Collect from the main module
        collect_tables_from_module(module)

        # If it's a package, also scan submodules
        if hasattr(module, "__path__"):
            for _, submodule_name, _ in pkgutil.walk_packages(
                module.__path__, prefix=module.__name__ + "."
            ):
                try:
                    submodule = importlib.import_module(submodule_name)
                    collect_tables_from_module(submodule)
                except ImportError:
                    continue

        return tables
    finally:
        # Clean up sys.path to avoid polluting the import path
        if added_cwd:
            sys.path.remove(".")
