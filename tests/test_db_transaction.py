"""Tests for transaction management."""

import pytest

from pykour.db import Database


@pytest.fixture
async def db():
    """Create an in-memory SQLite database."""
    database = Database("sqlite:///:memory:")
    await database.connect()

    # Create test table
    await database.execute(
        """
        CREATE TABLE accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # Insert initial data
    await database.execute(
        "INSERT INTO accounts (name, balance) VALUES ($1, $2)", "Alice", 100
    )
    await database.execute(
        "INSERT INTO accounts (name, balance) VALUES ($1, $2)", "Bob", 50
    )

    yield database

    await database.disconnect()


class TestTransaction:
    """Tests for transaction context manager."""

    async def test_commit_on_success(self, db: Database) -> None:
        """Transaction should commit on success."""
        async with await db.transaction():
            await db.execute(
                "UPDATE accounts SET balance = balance - 10 WHERE name = $1", "Alice"
            )
            await db.execute(
                "UPDATE accounts SET balance = balance + 10 WHERE name = $1", "Bob"
            )

        alice = await db.fetch_one("SELECT * FROM accounts WHERE name = $1", "Alice")
        bob = await db.fetch_one("SELECT * FROM accounts WHERE name = $1", "Bob")

        assert alice is not None
        assert bob is not None
        assert alice["balance"] == 90
        assert bob["balance"] == 60

    async def test_rollback_on_exception(self, db: Database) -> None:
        """Transaction should rollback on exception."""
        with pytest.raises(ValueError):
            async with await db.transaction():
                await db.execute(
                    "UPDATE accounts SET balance = balance - 10 WHERE name = $1",
                    "Alice",
                )
                raise ValueError("Something went wrong")

        alice = await db.fetch_one("SELECT * FROM accounts WHERE name = $1", "Alice")
        assert alice is not None
        assert alice["balance"] == 100  # Should be unchanged

    async def test_explicit_commit(self, db: Database) -> None:
        """Explicit commit should work."""
        tx = await db.transaction()
        async with tx:
            await db.execute(
                "UPDATE accounts SET balance = balance + 50 WHERE name = $1", "Alice"
            )
            await tx.commit()

        alice = await db.fetch_one("SELECT * FROM accounts WHERE name = $1", "Alice")
        assert alice is not None
        assert alice["balance"] == 150

    async def test_explicit_rollback(self, db: Database) -> None:
        """Explicit rollback should work."""
        tx = await db.transaction()
        async with tx:
            await db.execute(
                "UPDATE accounts SET balance = balance + 50 WHERE name = $1", "Alice"
            )
            await tx.rollback()

        alice = await db.fetch_one("SELECT * FROM accounts WHERE name = $1", "Alice")
        assert alice is not None
        assert alice["balance"] == 100  # Should be unchanged

    async def test_double_commit_is_noop(self, db: Database) -> None:
        """Double commit should be safe."""
        tx = await db.transaction()
        async with tx:
            await db.execute(
                "UPDATE accounts SET balance = 200 WHERE name = $1", "Alice"
            )
            await tx.commit()
            await tx.commit()  # Should not raise

        alice = await db.fetch_one("SELECT * FROM accounts WHERE name = $1", "Alice")
        assert alice is not None
        assert alice["balance"] == 200

    async def test_commit_after_rollback_raises(self, db: Database) -> None:
        """Commit after rollback should raise."""
        tx = await db.transaction()
        async with tx:
            await tx.rollback()
            with pytest.raises(RuntimeError, match="already rolled back"):
                await tx.commit()

    async def test_rollback_after_commit_raises(self, db: Database) -> None:
        """Rollback after commit should raise."""
        tx = await db.transaction()
        async with tx:
            await tx.commit()
            with pytest.raises(RuntimeError, match="already committed"):
                await tx.rollback()
