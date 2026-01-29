"""Pykour CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(args: list[str] | None = None) -> int:
    """Main CLI entry point.

    Args:
        args: Command line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code.
    """
    from dotenv import load_dotenv

    # Explicitly specify .env in the current working directory
    # (use user's working directory, not the entrypoint script location)
    load_dotenv(Path.cwd() / ".env")

    parser = argparse.ArgumentParser(
        prog="pykour",
        description="Pykour framework CLI",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    from pykour.cli.commands.generate import register_command as register_generate
    from pykour.cli.commands.migrate import register_command as register_migrate
    from pykour.cli.commands.routes import register_command as register_routes
    from pykour.cli.commands.run import register_command as register_run

    register_generate(subparsers)
    register_migrate(subparsers)
    register_routes(subparsers)
    register_run(subparsers)

    parsed = parser.parse_args(args)

    if parsed.command is None:
        parser.print_help()
        return 0

    if hasattr(parsed, "func"):
        return parsed.func(parsed)

    return 0


if __name__ == "__main__":
    sys.exit(main())
