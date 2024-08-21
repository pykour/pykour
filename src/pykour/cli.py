import argparse
import uvicorn
import signal
import sys
import asyncio
from functools import partial
import os

from pykour import __version__

usage_text = """usage: pykour [-h] {subcommand} ...

positional arguments:
    dev                 Run Web Server for Development
    run                 Run Web Server

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show Pykour version
"""

sys.path.append(os.getcwd())


class PykourArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        """Ignore unknown arguments."""
        ...  # pragma: no cover


def signal_handler(_signal, _frame):
    sys.exit(0)  # pragma: no cover


def parse_args(args):
    parser = PykourArgumentParser(description="Pykour CLI", add_help=False)

    parser.add_argument("-v", "--version", action="version", version=f"Pykour v{__version__}")
    parser.add_argument("-h", "--help", action="store_true", help="show this help message and exit")

    subparsers = parser.add_subparsers(dest="command")

    # Add the 'dev' subcommand
    dev_parser = subparsers.add_parser("dev", help="Run Web Server for Development")
    dev_parser.add_argument("app", type=str, help="The ASGI app instance to run, e.g., main:app")
    dev_parser.add_argument("--host", type=str, default="127.0.0.1", help="The host to bind to")
    dev_parser.add_argument("--port", type=int, default=8000, help="The port to bind to")
    dev_parser.add_argument("--reload", action="store_true", default=True, help="Enable auto-reload")
    dev_parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")

    # Add the 'run' subcommand
    run_parser = subparsers.add_parser("run", help="Run Web Server for Production")
    run_parser.add_argument("app", type=str, help="The ASGI app instance to run, e.g., main:app")
    run_parser.add_argument("--host", type=str, default="0.0.0.0", help="The host to bind to")
    run_parser.add_argument("--port", type=int, default=8000, help="The port to bind to")
    run_parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload")
    run_parser.add_argument("--workers", type=int, default=(os.cpu_count() * 2) + 1, help="Number of worker processes")

    # Parse the arguments
    return parser.parse_args(args)


def main(args=None):
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, partial(signal_handler, sig, None))

    if args is None:
        args = sys.argv[1:]
    args = parse_args(args)

    if args.help:
        print(usage_text)
        sys.exit(0)
    elif args.command == "dev":
        os.environ["PYKOUR_ENV"] = "development"

        uvicorn.run(
            args.app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            server_header=False,
        )
    elif args.command == "run":
        os.environ["PYKOUR_ENV"] = "production"

        uvicorn.run(
            args.app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            server_header=False,
        )

    else:
        print(usage_text)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
