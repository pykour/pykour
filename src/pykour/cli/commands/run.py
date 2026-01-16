"""Run command for starting the development server."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Any


def positive_int(value: str) -> int:
    """Validate that value is a positive integer (>= 1).

    Args:
        value: String value from command line argument.

    Returns:
        Parsed integer value.

    Raises:
        argparse.ArgumentTypeError: If value is not a positive integer.
    """
    try:
        ivalue = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid int value: '{value}'")
    if ivalue < 1:
        raise argparse.ArgumentTypeError(f"invalid value: {ivalue} (must be >= 1)")
    return ivalue


def register_command(subparsers: Any) -> None:
    """Register the run command."""
    run_parser = subparsers.add_parser(
        "run",
        help="Start the development server",
    )
    run_parser.add_argument(
        "app",
        type=str,
        help="Application module path (e.g., 'app:app' or 'main:application')",
    )
    run_parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind (default: 127.0.0.1)",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind (default: 8000)",
    )
    run_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes",
    )
    run_parser.add_argument(
        "--reload-dir",
        type=str,
        action="append",
        dest="reload_dirs",
        metavar="PATH",
        help="Specify directories to watch for changes (can be used multiple times)",
    )
    run_parser.add_argument(
        "--reload-include",
        type=str,
        action="append",
        dest="reload_includes",
        metavar="PATTERN",
        help="Glob pattern to include for watching (can be used multiple times)",
    )
    run_parser.add_argument(
        "--reload-exclude",
        type=str,
        action="append",
        dest="reload_excludes",
        metavar="PATTERN",
        help="Glob pattern to exclude from watching (can be used multiple times)",
    )
    run_parser.add_argument(
        "--workers",
        type=positive_int,
        default=1,
        help="Number of worker processes (default: 1)",
    )
    run_parser.add_argument(
        "--log-format",
        choices=["text", "json"],
        default="text",
        help="Log output format (default: text)",
    )
    run_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Log level (default: INFO)",
    )
    run_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (auto-enables reload, sets log level to DEBUG, shows tracebacks)",
    )
    run_parser.set_defaults(func=cmd_run)


def cmd_run(args: argparse.Namespace) -> int:
    """Start the development server.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    # Add current directory to sys.path for module imports
    import os

    cwd = os.getcwd()
    if cwd not in sys.path:
        sys.path.insert(0, cwd)

    try:
        import uvicorn
    except ImportError:
        print(
            "Error: uvicorn is required to run the server.\n"
            "Install it with: pip install pykour"
        )
        return 1

    # Parse application path
    module_path, _, app_name = args.app.partition(":")
    if not module_path:
        print(
            f"Error: Invalid application path: '{args.app}' — missing module name.\n"
            "Expected format: 'module:app' or 'module' (e.g., 'main:app', 'app:application')"
        )
        return 1
    if not app_name:
        app_name = "app"

    # Handle debug mode - auto-enable reload and DEBUG log level
    reload_enabled = args.reload or args.debug
    log_level = "DEBUG" if args.debug else args.log_level

    # Set environment variable for debug mode (application can read this)
    if args.debug:
        os.environ["PYKOUR_DEBUG"] = "1"

    # Configure logging
    _configure_logging(args.log_format, log_level)

    # Workers and reload are mutually exclusive
    workers = args.workers if not reload_enabled else 1
    if reload_enabled and args.workers > 1:
        print(
            "Warning: --reload/--debug is not compatible with --workers > 1. "
            "Running with 1 worker."
        )

    # Print startup message
    print("Starting Pykour server...")
    print(f"  Application: {module_path}:{app_name}")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Workers: {workers}")
    print(f"  Reload: {reload_enabled}")
    if args.debug:
        print("  Debug: True")
    if args.reload_dirs:
        print(f"  Reload dirs: {args.reload_dirs}")
    if args.reload_includes:
        print(f"  Reload include: {args.reload_includes}")
    if args.reload_excludes:
        print(f"  Reload exclude: {args.reload_excludes}")
    print(f"  Log format: {args.log_format}")
    print(f"  Log level: {log_level}")
    print()

    try:
        uvicorn.run(
            app=f"{module_path}:{app_name}",
            host=args.host,
            port=args.port,
            reload=reload_enabled,
            reload_dirs=args.reload_dirs,
            reload_includes=args.reload_includes,
            reload_excludes=args.reload_excludes,
            workers=workers,
            access_log=False,  # Pykour LoggingMiddleware handles this
            log_level=log_level.lower(),
        )
        return 0
    except KeyboardInterrupt:
        print("\nServer stopped.")
        return 0
    except Exception as e:
        print(f"Error starting server: {e}")
        return 1


def _configure_logging(format_type: str, level: str) -> None:
    """Configure logging based on CLI options.

    Args:
        format_type: Log format ("text" or "json").
        level: Log level string.
    """
    from pykour.logging import JsonFormatter, TextFormatter, TraceLogFilter

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level))

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create new handler with appropriate formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.addFilter(TraceLogFilter())

    if format_type == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter())

    root_logger.addHandler(handler)

    # Also configure pykour loggers
    pykour_logger = logging.getLogger("pykour")
    pykour_logger.setLevel(getattr(logging, level))
