"""Command registration for migrate subcommands."""

from __future__ import annotations

from typing import Any

from pykour.cli.commands.migrate.basic import (
    cmd_down,
    cmd_generate,
    cmd_init,
    cmd_new,
    cmd_up,
)
from pykour.cli.commands.migrate.inspect import cmd_history, cmd_status
from pykour.cli.commands.migrate.maintenance import cmd_archive, cmd_squash


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
