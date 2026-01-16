"""Routes command for displaying registered routes."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def register_command(subparsers: Any) -> None:
    """Register the routes command."""
    routes_parser = subparsers.add_parser(
        "routes",
        help="Display registered routes",
    )
    routes_parser.add_argument(
        "--routes-dir",
        type=str,
        default="routes",
        help="Routes directory path (default: routes)",
    )
    routes_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed route information",
    )
    routes_parser.set_defaults(func=cmd_routes)


def cmd_routes(args: argparse.Namespace) -> int:
    """Display registered routes.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    from pykour.router import Router

    routes_dir = Path(args.routes_dir)

    if not routes_dir.exists():
        print(f"Error: Routes directory '{routes_dir}' not found.")
        return 1

    try:
        router = Router(routes_dir)
    except Exception as e:
        print(f"Error loading routes: {e}")
        return 1

    if not router.routes:
        print("No routes found.")
        return 0

    print(f"\nRegistered routes ({len(router.routes)} total):\n")

    for route in router.routes:
        methods = sorted(route.handlers.keys())
        methods_str = ", ".join(m.upper() for m in methods)

        if args.verbose:
            print(f"  {route.path_pattern}")
            print(f"    Methods: {methods_str}")
            if route.param_names:
                print(f"    Parameters: {', '.join(route.param_names)}")
            if route.is_catch_all:
                print("    Catch-all: Yes")
            print()
        else:
            print(f"  {methods_str:30} {route.path_pattern}")

    print()
    return 0
