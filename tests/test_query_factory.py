"""Tests for QueryBuilderFactory."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pykour.db.query import DeleteQuery, InsertQuery, SelectQuery, UpdateQuery
from pykour.db.query_factory import QueryBuilderFactory
from pykour.db.result import Row


class MockConnectionManager:
    """Mock connection manager for testing."""

    def __init__(self) -> None:
        self._connected = True
        self.transaction_connection: Any = None
        self.executed_queries: list[tuple[str, tuple[Any, ...]]] = []
        self._commit_called = False

    async def acquire(self) -> str:
        return "mock_conn"

    async def release(self, conn: Any) -> None:
        pass

    async def execute(self, conn: Any, sql: str, args: tuple[Any, ...]) -> int:
        self.executed_queries.append((sql, args))
        return 1

    async def fetch_all(self, conn: Any, sql: str, args: tuple[Any, ...]) -> list[Row]:
        self.executed_queries.append((sql, args))
        return []

    async def fetch_one(self, conn: Any, sql: str, args: tuple[Any, ...]) -> Row | None:
        self.executed_queries.append((sql, args))
        return None

    async def commit(self, conn: Any) -> None:
        self._commit_called = True

    def check_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Database is not connected")

    def convert_placeholders(self, sql: str, count: int) -> str:
        return sql


class MockPolicyManager:
    """Mock policy manager for testing."""

    def get_policy_kwargs(self) -> dict[str, Any]:
        return {
            "policy_enforcer": None,
            "table_policies": {},
            "get_policy_context": lambda: None,
        }


class TestQueryBuilderFactoryInit:
    """Tests for QueryBuilderFactory initialization."""

    def test_init_stores_connection_manager(self) -> None:
        """Connection manager should be stored."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()

        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        assert factory._conn is conn_manager

    def test_init_stores_policy_manager(self) -> None:
        """Policy manager should be stored."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()

        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        assert factory._policy is policy_manager


class TestQueryBuilderFactorySelect:
    """Tests for select method."""

    def test_select_returns_select_query(self) -> None:
        """Should return SelectQuery instance."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        query = factory.select("*")

        assert isinstance(query, SelectQuery)

    def test_select_with_columns(self) -> None:
        """Should pass columns to SelectQuery."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        query = factory.select("id", "name", "email")

        assert query._columns == ("id", "name", "email")

    def test_select_checks_connected(self) -> None:
        """Should raise if not connected."""
        conn_manager = MockConnectionManager()
        conn_manager._connected = False
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        with pytest.raises(RuntimeError, match="not connected"):
            factory.select("*")


class TestQueryBuilderFactoryInsert:
    """Tests for insert method."""

    def test_insert_returns_insert_query(self) -> None:
        """Should return InsertQuery instance."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        query = factory.insert("users")

        assert isinstance(query, InsertQuery)

    def test_insert_with_table(self) -> None:
        """Should pass table to InsertQuery."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        query = factory.insert("users")

        assert query._table == "users"

    def test_insert_checks_connected(self) -> None:
        """Should raise if not connected."""
        conn_manager = MockConnectionManager()
        conn_manager._connected = False
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        with pytest.raises(RuntimeError, match="not connected"):
            factory.insert("users")


class TestQueryBuilderFactoryUpdate:
    """Tests for update method."""

    def test_update_returns_update_query(self) -> None:
        """Should return UpdateQuery instance."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        query = factory.update("users")

        assert isinstance(query, UpdateQuery)

    def test_update_with_table(self) -> None:
        """Should pass table to UpdateQuery."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        query = factory.update("users")

        assert query._table == "users"

    def test_update_checks_connected(self) -> None:
        """Should raise if not connected."""
        conn_manager = MockConnectionManager()
        conn_manager._connected = False
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        with pytest.raises(RuntimeError, match="not connected"):
            factory.update("users")


class TestQueryBuilderFactoryDelete:
    """Tests for delete method."""

    def test_delete_returns_delete_query(self) -> None:
        """Should return DeleteQuery instance."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        query = factory.delete("users")

        assert isinstance(query, DeleteQuery)

    def test_delete_with_table(self) -> None:
        """Should pass table to DeleteQuery."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        query = factory.delete("users")

        assert query._table == "users"

    def test_delete_checks_connected(self) -> None:
        """Should raise if not connected."""
        conn_manager = MockConnectionManager()
        conn_manager._connected = False
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        with pytest.raises(RuntimeError, match="not connected"):
            factory.delete("users")


class TestQueryBuilderFactoryExecuteMethods:
    """Tests for internal execute methods."""

    async def test_execute_for_query_acquires_connection(self) -> None:
        """Should acquire and release connection."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        result = await factory._execute_for_query(
            "INSERT INTO users (name) VALUES ($1)", ("Alice",)
        )

        assert result == 1
        assert len(conn_manager.executed_queries) == 1

    async def test_execute_for_query_converts_placeholders(self) -> None:
        """Should convert placeholders before execution."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        await factory._execute_for_query(
            "INSERT INTO users (name, age) VALUES ($1, $2)", ("Alice", 30)
        )

        # Check that placeholders were processed
        assert len(conn_manager.executed_queries) == 1

    async def test_execute_for_query_auto_commits(self) -> None:
        """Should auto-commit when not in transaction."""
        conn_manager = MockConnectionManager()
        conn_manager.transaction_connection = None
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        await factory._execute_for_query(
            "INSERT INTO users (name) VALUES ($1)", ("Alice",)
        )

        assert conn_manager._commit_called is True

    async def test_execute_for_query_no_commit_in_transaction(self) -> None:
        """Should not commit when in transaction."""
        conn_manager = MockConnectionManager()
        conn_manager.transaction_connection = "active_transaction"
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        await factory._execute_for_query(
            "INSERT INTO users (name) VALUES ($1)", ("Alice",)
        )

        assert conn_manager._commit_called is False

    async def test_fetch_all_for_query(self) -> None:
        """Should fetch all rows."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        result = await factory._fetch_all_for_query("SELECT * FROM users", ())

        assert result == []
        assert len(conn_manager.executed_queries) == 1

    async def test_fetch_one_for_query(self) -> None:
        """Should fetch one row."""
        conn_manager = MockConnectionManager()
        policy_manager = MockPolicyManager()
        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,  # type: ignore[arg-type]
        )

        result = await factory._fetch_one_for_query(
            "SELECT * FROM users WHERE id = $1", (1,)
        )

        assert result is None
        assert len(conn_manager.executed_queries) == 1


class TestQueryBuilderFactoryPolicyIntegration:
    """Tests for policy kwargs integration."""

    def test_select_includes_policy_kwargs(self) -> None:
        """Should pass policy kwargs to query."""
        conn_manager = MockConnectionManager()
        mock_enforcer = MagicMock()
        mock_policies = {"users": MagicMock()}
        mock_context_func = MagicMock()

        policy_manager = MagicMock()
        policy_manager.get_policy_kwargs.return_value = {
            "policy_enforcer": mock_enforcer,
            "table_policies": mock_policies,
            "get_policy_context": mock_context_func,
        }

        factory = QueryBuilderFactory(
            conn_manager,  # type: ignore[arg-type]
            policy_manager,
        )
        query = factory.select("*")

        # Verify policy kwargs were passed
        policy_manager.get_policy_kwargs.assert_called_once()
        assert query._policy_enforcer is mock_enforcer
        assert query._table_policies is mock_policies
        assert query._get_policy_context is mock_context_func
