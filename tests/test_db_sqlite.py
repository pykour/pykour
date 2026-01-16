"""Tests for SQLite driver and database integration."""

import pytest

from pykour.db import Database, Row


@pytest.fixture
async def db():
    """Create an in-memory SQLite database."""
    database = Database("sqlite:///:memory:")
    await database.connect()

    # Create test table
    await database.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            active INTEGER DEFAULT 1
        )
        """
    )

    yield database

    await database.disconnect()


class TestDatabaseConnection:
    """Tests for database connection."""

    async def test_connect_disconnect(self) -> None:
        """Connect and disconnect should work."""
        db = Database("sqlite:///:memory:")
        await db.connect()
        await db.disconnect()

    async def test_double_connect(self) -> None:
        """Double connect should be idempotent."""
        db = Database("sqlite:///:memory:")
        await db.connect()
        await db.connect()  # Should not raise
        await db.disconnect()

    async def test_double_disconnect(self) -> None:
        """Double disconnect should be idempotent."""
        db = Database("sqlite:///:memory:")
        await db.connect()
        await db.disconnect()
        await db.disconnect()  # Should not raise


class TestRawQueries:
    """Tests for raw SQL queries."""

    async def test_execute(self, db: Database) -> None:
        """Execute should work."""
        result = await db.execute(
            "INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30
        )
        assert result >= 0

    async def test_fetch_all(self, db: Database) -> None:
        """fetch_all should return list of rows."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Bob", 25)

        rows = await db.fetch_all("SELECT * FROM users")
        assert len(rows) == 2
        assert all(isinstance(row, Row) for row in rows)

    async def test_fetch_one(self, db: Database) -> None:
        """fetch_one should return a single row."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)

        row = await db.fetch_one("SELECT * FROM users WHERE name = $1", "Alice")
        assert row is not None
        assert row["name"] == "Alice"
        assert row.age == 30  # Attribute access

    async def test_fetch_one_not_found(self, db: Database) -> None:
        """fetch_one should return None when not found."""
        row = await db.fetch_one("SELECT * FROM users WHERE name = $1", "Nobody")
        assert row is None

    async def test_fetch_val(self, db: Database) -> None:
        """fetch_val should return a single value."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)

        count = await db.fetch_val("SELECT COUNT(*) FROM users")
        assert count == 1


class TestQueryBuilder:
    """Tests for query builder methods."""

    async def test_select_all(self, db: Database) -> None:
        """SELECT * should work."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)

        rows = await db.select("*").from_("users").fetch_all()
        assert len(rows) == 1
        assert rows[0]["name"] == "Alice"

    async def test_select_columns(self, db: Database) -> None:
        """SELECT with specific columns."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)

        rows = await db.select("name", "age").from_("users").fetch_all()
        assert len(rows) == 1
        assert "name" in rows[0]
        assert "age" in rows[0]

    async def test_select_where(self, db: Database) -> None:
        """SELECT with WHERE clause."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Bob", 25)

        rows = await db.select("*").from_("users").where(name="Alice").fetch_all()
        assert len(rows) == 1
        assert rows[0]["name"] == "Alice"

    async def test_select_order_by(self, db: Database) -> None:
        """SELECT with ORDER BY."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Bob", 25)

        rows = await db.select("*").from_("users").order_by("age").fetch_all()
        assert rows[0]["name"] == "Bob"  # Younger first

    async def test_select_limit(self, db: Database) -> None:
        """SELECT with LIMIT."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Bob", 25)

        rows = await db.select("*").from_("users").limit(1).fetch_all()
        assert len(rows) == 1

    async def test_insert(self, db: Database) -> None:
        """INSERT should work."""
        await db.insert("users").values(name="Alice", age=30).execute()

        row = await db.fetch_one("SELECT * FROM users WHERE name = $1", "Alice")
        assert row is not None
        assert row["age"] == 30

    async def test_insert_returning(self, db: Database) -> None:
        """INSERT with RETURNING should work."""
        row = (
            await db.insert("users")
            .values(name="Alice", age=30)
            .returning("id")
            .fetch_one()
        )
        assert row is not None
        assert row["id"] is not None

    async def test_update(self, db: Database) -> None:
        """UPDATE should work."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)

        await db.update("users").set(age=31).where(name="Alice").execute()

        row = await db.fetch_one("SELECT * FROM users WHERE name = $1", "Alice")
        assert row is not None
        assert row["age"] == 31

    async def test_delete(self, db: Database) -> None:
        """DELETE should work."""
        await db.execute("INSERT INTO users (name, age) VALUES ($1, $2)", "Alice", 30)

        await db.delete("users").where(name="Alice").execute()

        row = await db.fetch_one("SELECT * FROM users WHERE name = $1", "Alice")
        assert row is None


class TestRow:
    """Tests for Row class."""

    def test_dict_access(self) -> None:
        """Row should support dict access."""
        row = Row({"id": 1, "name": "Alice"})
        assert row["id"] == 1
        assert row["name"] == "Alice"

    def test_attr_access(self) -> None:
        """Row should support attribute access."""
        row = Row({"id": 1, "name": "Alice"})
        assert row.id == 1
        assert row.name == "Alice"

    def test_attr_error(self) -> None:
        """Row should raise AttributeError for missing attributes."""
        row = Row({"id": 1})
        with pytest.raises(AttributeError):
            _ = row.nonexistent

    def test_repr(self) -> None:
        """Row repr should include values."""
        row = Row({"id": 1, "name": "Alice"})
        assert "id=1" in repr(row)
        assert "Alice" in repr(row)
