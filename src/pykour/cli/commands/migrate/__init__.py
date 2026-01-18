"""Migrate command for database migrations.

This package provides migration management commands including:
- init: Initialize migrations directory and database table
- new: Create an empty migration file
- generate: Generate migration from schema diff
- up/down: Apply or rollback migrations
- status/history: View migration state
- squash: Combine multiple migrations
- archive: Freeze migrations to prevent modification
"""

from pykour.cli.commands.migrate.maintenance import _check_archive_boundary
from pykour.cli.commands.migrate.registry import register_command

__all__ = ["register_command", "_check_archive_boundary"]
