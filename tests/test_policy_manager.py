"""Tests for AccessPolicyManager."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from pykour.db.policy_manager import AccessPolicyManager


class TestAccessPolicyManagerInit:
    """Tests for AccessPolicyManager initialization."""

    def test_init_default_enabled(self) -> None:
        """Policies should be enabled by default."""
        manager = AccessPolicyManager()
        assert manager.enabled is True

    def test_init_disabled(self) -> None:
        """Policies can be disabled via constructor."""
        manager = AccessPolicyManager(enable_policies=False)
        assert manager.enabled is False

    def test_init_empty_policies(self) -> None:
        """Initial table_policies should be empty dict."""
        manager = AccessPolicyManager()
        assert manager.table_policies == {}

    def test_init_no_enforcer(self) -> None:
        """Initial enforcer should be None."""
        manager = AccessPolicyManager()
        assert manager.enforcer is None


class TestAccessPolicyManagerProperties:
    """Tests for AccessPolicyManager properties."""

    def test_enabled_property(self) -> None:
        """enabled property should reflect _enable_policies."""
        manager = AccessPolicyManager(enable_policies=True)
        assert manager.enabled is True

        manager = AccessPolicyManager(enable_policies=False)
        assert manager.enabled is False

    def test_enforcer_property(self) -> None:
        """enforcer property should return _policy_enforcer."""
        manager = AccessPolicyManager()
        manager._policy_enforcer = MagicMock()
        assert manager.enforcer is manager._policy_enforcer

    def test_table_policies_property(self) -> None:
        """table_policies property should return registered policies."""
        manager = AccessPolicyManager()
        mock_policy = MagicMock()
        manager._table_policies["users"] = mock_policy
        assert manager.table_policies == {"users": mock_policy}


class TestAccessPolicyManagerInitializeEnforcer:
    """Tests for initialize_enforcer method."""

    def test_initialize_sqlite_enforcer(self) -> None:
        """SQLite enforcer should be initialized."""
        manager = AccessPolicyManager()
        with patch(
            "pykour.db.access_policy.enforcer.get_enforcer"
        ) as mock_get_enforcer:
            mock_enforcer = MagicMock()
            mock_get_enforcer.return_value = mock_enforcer

            manager.initialize_enforcer("sqlite")

            mock_get_enforcer.assert_called_once_with("sqlite")
            assert manager.enforcer is mock_enforcer

    def test_initialize_postgresql_enforcer(self) -> None:
        """PostgreSQL enforcer should be initialized."""
        manager = AccessPolicyManager()
        with patch(
            "pykour.db.access_policy.enforcer.get_enforcer"
        ) as mock_get_enforcer:
            mock_enforcer = MagicMock()
            mock_get_enforcer.return_value = mock_enforcer

            manager.initialize_enforcer("postgresql")

            mock_get_enforcer.assert_called_once_with("postgresql")
            assert manager.enforcer is mock_enforcer

    def test_initialize_mysql_enforcer(self) -> None:
        """MySQL enforcer should be initialized."""
        manager = AccessPolicyManager()
        with patch(
            "pykour.db.access_policy.enforcer.get_enforcer"
        ) as mock_get_enforcer:
            mock_enforcer = MagicMock()
            mock_get_enforcer.return_value = mock_enforcer

            manager.initialize_enforcer("mysql")

            mock_get_enforcer.assert_called_once_with("mysql")
            assert manager.enforcer is mock_enforcer

    def test_initialize_when_disabled(self) -> None:
        """Should not initialize enforcer when policies disabled."""
        manager = AccessPolicyManager(enable_policies=False)

        manager.initialize_enforcer("sqlite")

        # When disabled, enforcer should remain None
        assert manager.enforcer is None


class TestAccessPolicyManagerRegisterTable:
    """Tests for register_table method."""

    def test_register_table_with_tablename(self) -> None:
        """Table with __tablename__ should use it."""
        manager = AccessPolicyManager()
        mock_policy = MagicMock()

        class MyTable:
            __tablename__ = "my_custom_table"
            __access_policy__ = mock_policy

        manager.register_table(MyTable)

        assert "my_custom_table" in manager.table_policies
        assert manager.table_policies["my_custom_table"] is mock_policy

    def test_register_table_without_tablename(self) -> None:
        """Table without __tablename__ should use lowercased class name."""
        manager = AccessPolicyManager()
        mock_policy = MagicMock()

        class UserTable:
            __access_policy__ = mock_policy

        manager.register_table(UserTable)

        assert "usertable" in manager.table_policies
        assert manager.table_policies["usertable"] is mock_policy

    def test_register_table_with_policy(self) -> None:
        """Table with __access_policy__ should register policy."""
        manager = AccessPolicyManager()
        mock_policy = MagicMock()

        class MyTable:
            __tablename__ = "my_table"
            __access_policy__ = mock_policy

        manager.register_table(MyTable)

        assert manager.get_policy("my_table") is mock_policy

    def test_register_table_without_policy(self) -> None:
        """Table without __access_policy__ should not register policy."""
        manager = AccessPolicyManager()

        class MyTable:
            __tablename__ = "my_table"

        manager.register_table(MyTable)

        assert "my_table" not in manager.table_policies


class TestAccessPolicyManagerRegisterPolicy:
    """Tests for register_policy method."""

    def test_register_policy_basic(self) -> None:
        """Policy should be registered with table name."""
        manager = AccessPolicyManager()
        mock_policy = MagicMock()

        manager.register_policy("orders", mock_policy)

        assert manager.table_policies["orders"] is mock_policy

    def test_register_policy_overwrite(self) -> None:
        """Registering same table should overwrite existing policy."""
        manager = AccessPolicyManager()
        policy1 = MagicMock()
        policy2 = MagicMock()

        manager.register_policy("users", policy1)
        manager.register_policy("users", policy2)

        assert manager.table_policies["users"] is policy2


class TestAccessPolicyManagerGetPolicy:
    """Tests for get_policy method."""

    def test_get_existing_policy(self) -> None:
        """Should return registered policy."""
        manager = AccessPolicyManager()
        mock_policy = MagicMock()
        manager.register_policy("users", mock_policy)

        result = manager.get_policy("users")

        assert result is mock_policy

    def test_get_nonexistent_policy(self) -> None:
        """Should return None for unregistered table."""
        manager = AccessPolicyManager()

        result = manager.get_policy("nonexistent")

        assert result is None


class TestAccessPolicyManagerGetPolicyContext:
    """Tests for get_policy_context method."""

    def test_get_context_returns_from_module(self) -> None:
        """Should return current policy context from module."""
        manager = AccessPolicyManager()

        with patch(
            "pykour.db.access_policy.context.get_policy_context"
        ) as mock_get_context:
            mock_context = {"user_id": 123}
            mock_get_context.return_value = mock_context

            result = manager.get_policy_context()

            mock_get_context.assert_called_once()
            assert result == mock_context


class TestAccessPolicyManagerGetPolicyKwargs:
    """Tests for get_policy_kwargs method."""

    def test_returns_correct_structure(self) -> None:
        """Should return dict with required keys."""
        manager = AccessPolicyManager()

        kwargs = manager.get_policy_kwargs()

        assert "policy_enforcer" in kwargs
        assert "table_policies" in kwargs
        assert "get_policy_context" in kwargs

    def test_includes_enforcer(self) -> None:
        """Should include policy_enforcer."""
        manager = AccessPolicyManager()
        mock_enforcer = MagicMock()
        manager._policy_enforcer = mock_enforcer

        kwargs = manager.get_policy_kwargs()

        assert kwargs["policy_enforcer"] is mock_enforcer

    def test_includes_table_policies(self) -> None:
        """Should include table_policies dict."""
        manager = AccessPolicyManager()
        mock_policy = MagicMock()
        manager.register_policy("users", mock_policy)

        kwargs = manager.get_policy_kwargs()

        assert kwargs["table_policies"] == {"users": mock_policy}

    def test_includes_get_context_func(self) -> None:
        """Should include get_policy_context callable."""
        manager = AccessPolicyManager()

        kwargs = manager.get_policy_kwargs()

        assert callable(kwargs["get_policy_context"])
        assert kwargs["get_policy_context"] == manager.get_policy_context
