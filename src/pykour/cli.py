import argparse
import uvicorn
import signal
import sys
import asyncio
from functools import partial


def signal_handler(_signal, _frame):
    sys.exit(0)


def main():
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, partial(signal_handler, sig, None))

    parser = argparse.ArgumentParser(description="Pykour CLI")
    subparsers = parser.add_subparsers(dest="command", help="sub-command help")

    # Add the 'help' command
    subparsers.add_parser("help", help="Print the help")

    # Add the 'version' command
    subparsers.add_parser("version", help="Print the version")

    # Add the 'run' command
    run_parser = subparsers.add_parser("run", help="Run Web Server")
    run_parser.add_argument("app", type=str, help="The ASGI app instance to run, e.g., main:app")
    run_parser.add_argument("--host", type=str, default="127.0.0.1", help="The host to bind to")
    run_parser.add_argument("--port", type=int, default=8000, help="The port to bind to")
    run_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    run_parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")

    # Parse the arguments
    args = parser.parse_args()

    if args.command == "run":
        uvicorn.run(
            args.app,
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers,
            server_header=False,
        )
    elif args.command == "version":
        print("Pykour v0.1.1")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
