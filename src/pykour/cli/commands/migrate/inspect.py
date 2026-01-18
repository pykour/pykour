"""Inspection commands: status, history."""

from __future__ import annotations

import argparse
import asyncio

from pykour.cli.commands.migrate.utils import get_runner


def cmd_status(args: argparse.Namespace) -> int:
    """Show migration status."""

    async def run() -> int:
        runner, db = await get_runner(args)
        try:
            status = await runner.status()

            print(f"Current version: {status['current_version'] or 'None'}")
            print(f"Total migrations: {status['total_migrations']}")
            print(f"Applied: {status['applied_count']}")
            print(f"Pending: {status['pending_count']}")

            if status["pending"]:
                print("\nPending migrations:")
                for m in status["pending"]:
                    print(f"  {m['version']} - {m['name']}")

            return 0
        finally:
            await db.disconnect()

    return asyncio.run(run())


def cmd_history(args: argparse.Namespace) -> int:
    """Show migration history."""

    async def run() -> int:
        runner, db = await get_runner(args)
        try:
            history = await runner.history()

            if history:
                print("Migration history:")
                for m in history:
                    print(f"  {m['version']} - {m['name']} ({m['applied_at']})")
            else:
                print("No migrations applied yet")

            return 0
        finally:
            await db.disconnect()

    return asyncio.run(run())
