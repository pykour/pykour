"""Tests for AccessPolicy module."""

from __future__ import annotations

import pytest

from pykour.db.access_policy import (
    AccessPolicy,
    PolicyRule,
    PolicyAction,
    PolicyContextData,
    get_policy_context,
    set_policy_context,
    clear_policy_context,
    PolicyContextManager,
    ApplicationLevelEnforcer,
    get_enforcer,
)


class TestPolicyRule:
    """Tests for PolicyRule class."""

    def test_get_required_context_keys_single(self) -> None:
        """Test extracting single context key."""
        rule = PolicyRule("tenant_id = :tenant_id")
        keys = rule.get_required_context_keys()
        assert keys == {"tenant_id"}

    def test_get_required_context_keys_multiple(self) -> None:
        """Test extracting multiple context keys."""
        rule = PolicyRule("tenant_id = :tenant_id AND user_id = :user_id")
        keys = rule.get_required_context_keys()
        assert keys == {"tenant_id", "user_id"}

    def test_get_required_context_keys_with_or(self) -> None:
        """Test with OR conditions."""
        rule = PolicyRule("user_id = :user_id OR is_public = true")
        keys = rule.get_required_context_keys()
        assert keys == {"user_id"}

    def test_render_single_param(self) -> None:
        """Test rendering with single parameter."""
        rule = PolicyRule("tenant_id = :tenant_id")
        rendered, params = rule.render({"tenant_id": "t123"}, param_offset=0)
        assert rendered == "tenant_id = $1"
        assert params == ["t123"]

    def test_render_with_offset(self) -> None:
        """Test rendering with parameter offset."""
        rule = PolicyRule("tenant_id = :tenant_id")
        rendered, params = rule.render({"tenant_id": "t123"}, param_offset=2)
        assert rendered == "tenant_id = $3"
        assert params == ["t123"]

    def test_render_multiple_params(self) -> None:
        """Test rendering with multiple parameters."""
        rule = PolicyRule("tenant_id = :tenant_id AND user_id = :user_id")
        rendered, params = rule.render(
            {"tenant_id": "t123", "user_id": "u456"}, param_offset=0
        )
        assert rendered == "tenant_id = $1 AND user_id = $2"
        assert params == ["t123", "u456"]


class TestAccessPolicy:
    """Tests for AccessPolicy class."""

    def test_get_rules_for_select(self) -> None:
        """Test getting rules for SELECT action."""
        policy = AccessPolicy(
            select=["tenant_id = :tenant_id"],
            update=["user_id = :user_id"],
        )
        rules = policy.get_rules_for_action(PolicyAction.SELECT)
        assert len(rules) == 1
        assert rules[0].condition == "tenant_id = :tenant_id"

    def test_get_rules_for_update(self) -> None:
        """Test getting rules for UPDATE action."""
        policy = AccessPolicy(
            select=["tenant_id = :tenant_id"],
            update=["user_id = :user_id"],
        )
        rules = policy.get_rules_for_action(PolicyAction.UPDATE)
        assert len(rules) == 1
        assert rules[0].condition == "user_id = :user_id"

    def test_get_all_required_context_keys(self) -> None:
        """Test getting all required context keys."""
        policy = AccessPolicy(
            select=["tenant_id = :tenant_id"],
            update=["tenant_id = :tenant_id", "user_id = :user_id"],
            auto_set={"org_id": ":organization_id"},
        )
        keys = policy.get_all_required_context_keys()
        assert keys == {"tenant_id", "user_id", "organization_id"}

    def test_get_auto_set_values(self) -> None:
        """Test getting auto-set values."""
        policy = AccessPolicy(
            auto_set={"tenant_id": ":tenant_id", "fixed": "value"},
        )
        values = policy.get_auto_set_values({"tenant_id": "t123"})
        assert values == {"tenant_id": "t123", "fixed": "value"}

    def test_should_bypass_with_matching_role(self) -> None:
        """Test bypass check with matching role."""
        policy = AccessPolicy(bypass_roles=["admin", "superuser"])
        assert policy.should_bypass(["admin"]) is True
        assert policy.should_bypass(["user", "admin"]) is True

    def test_should_bypass_without_matching_role(self) -> None:
        """Test bypass check without matching role."""
        policy = AccessPolicy(bypass_roles=["admin"])
        assert policy.should_bypass(["user"]) is False
        assert policy.should_bypass([]) is False

    def test_should_bypass_empty_roles(self) -> None:
        """Test bypass check with no bypass_roles defined."""
        policy = AccessPolicy()
        assert policy.should_bypass(["admin"]) is False


class TestPolicyContext:
    """Tests for PolicyContext functions."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        clear_policy_context()

    def test_set_and_get_context(self) -> None:
        """Test setting and getting policy context."""
        set_policy_context(tenant_id="t1", user_id="u1")
        ctx = get_policy_context()
        assert ctx is not None
        assert ctx.tenant_id == "t1"
        assert ctx.user_id == "u1"

    def test_clear_context(self) -> None:
        """Test clearing policy context."""
        set_policy_context(tenant_id="t1")
        clear_policy_context()
        ctx = get_policy_context()
        assert ctx is None

    def test_custom_keys(self) -> None:
        """Test custom context keys."""
        set_policy_context(department_id="d1")
        ctx = get_policy_context()
        assert ctx is not None
        assert ctx.get("department_id") == "d1"

    def test_bypass_enforcement(self) -> None:
        """Test bypass_enforcement flag."""
        set_policy_context(bypass_enforcement=True)
        ctx = get_policy_context()
        assert ctx is not None
        assert ctx.bypass_enforcement is True

    def test_roles(self) -> None:
        """Test roles list."""
        set_policy_context(roles=["admin", "user"])
        ctx = get_policy_context()
        assert ctx is not None
        assert ctx.roles == ["admin", "user"]


class TestPolicyContextManager:
    """Tests for PolicyContextManager."""

    def teardown_method(self) -> None:
        """Clean up after each test."""
        clear_policy_context()

    def test_context_manager_sets_context(self) -> None:
        """Test that context manager sets policy context."""
        with PolicyContextManager(tenant_id="t2"):
            ctx = get_policy_context()
            assert ctx is not None
            assert ctx.tenant_id == "t2"

    def test_context_manager_clears_on_exit(self) -> None:
        """Test that context manager clears context on exit."""
        with PolicyContextManager(tenant_id="t2"):
            pass
        ctx = get_policy_context()
        assert ctx is None

    def test_context_manager_restores_previous(self) -> None:
        """Test that context manager restores previous context."""
        set_policy_context(tenant_id="outer")
        with PolicyContextManager(tenant_id="inner"):
            ctx = get_policy_context()
            assert ctx is not None
            assert ctx.tenant_id == "inner"
        ctx = get_policy_context()
        assert ctx is not None
        assert ctx.tenant_id == "outer"

    @pytest.mark.asyncio
    async def test_async_context_manager(self) -> None:
        """Test async context manager."""
        async with PolicyContextManager(tenant_id="async_t"):
            ctx = get_policy_context()
            assert ctx is not None
            assert ctx.tenant_id == "async_t"
        ctx = get_policy_context()
        assert ctx is None


class TestPolicyContextData:
    """Tests for PolicyContextData class."""

    def test_get_standard_keys(self) -> None:
        """Test getting standard context keys."""
        ctx = PolicyContextData(tenant_id="t1", user_id="u1")
        assert ctx.get("tenant_id") == "t1"
        assert ctx.get("user_id") == "u1"

    def test_get_custom_keys(self) -> None:
        """Test getting custom context keys."""
        ctx = PolicyContextData(custom={"custom_key": "value"})
        assert ctx.get("custom_key") == "value"

    def test_to_dict(self) -> None:
        """Test converting to dictionary."""
        ctx = PolicyContextData(
            tenant_id="t1",
            user_id="u1",
            custom={"extra": "value"},
        )
        d = ctx.to_dict()
        assert d["tenant_id"] == "t1"
        assert d["user_id"] == "u1"
        assert d["extra"] == "value"


class TestApplicationLevelEnforcer:
    """Tests for ApplicationLevelEnforcer."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.enforcer = ApplicationLevelEnforcer()

    def teardown_method(self) -> None:
        """Clean up after each test."""
        clear_policy_context()

    def test_apply_to_select_no_policy(self) -> None:
        """Test SELECT with no policy rules."""
        policy = AccessPolicy()
        context = PolicyContextData(tenant_id="t1")
        sql = "SELECT * FROM orders"
        new_sql, new_args = self.enforcer.apply_to_select(
            sql, (), "orders", policy, context
        )
        assert new_sql == sql
        assert new_args == ()

    def test_apply_to_select_with_policy(self) -> None:
        """Test SELECT with policy rules."""
        policy = AccessPolicy(select=["tenant_id = :tenant_id"])
        context = PolicyContextData(tenant_id="t123")
        sql = "SELECT * FROM orders"
        new_sql, new_args = self.enforcer.apply_to_select(
            sql, (), "orders", policy, context
        )
        assert "WHERE" in new_sql
        assert "(tenant_id = $1)" in new_sql
        assert new_args == ("t123",)

    def test_apply_to_select_append_to_existing_where(self) -> None:
        """Test SELECT appending to existing WHERE clause."""
        policy = AccessPolicy(select=["tenant_id = :tenant_id"])
        context = PolicyContextData(tenant_id="t123")
        sql = "SELECT * FROM orders WHERE status = $1"
        new_sql, new_args = self.enforcer.apply_to_select(
            sql, ("active",), "orders", policy, context
        )
        # Policy conditions are prepended to existing WHERE clause
        assert "WHERE ((tenant_id = $2)) AND" in new_sql
        assert "status = $1" in new_sql
        assert new_args == ("active", "t123")

    def test_apply_to_select_bypass(self) -> None:
        """Test SELECT with bypass enforcement."""
        policy = AccessPolicy(select=["tenant_id = :tenant_id"])
        context = PolicyContextData(tenant_id="t123", bypass_enforcement=True)
        sql = "SELECT * FROM orders"
        new_sql, new_args = self.enforcer.apply_to_select(
            sql, (), "orders", policy, context
        )
        assert new_sql == sql
        assert new_args == ()

    def test_apply_to_select_bypass_role(self) -> None:
        """Test SELECT with bypass role."""
        policy = AccessPolicy(
            select=["tenant_id = :tenant_id"],
            bypass_roles=["admin"],
        )
        context = PolicyContextData(tenant_id="t123", roles=["admin"])
        sql = "SELECT * FROM orders"
        new_sql, new_args = self.enforcer.apply_to_select(
            sql, (), "orders", policy, context
        )
        assert new_sql == sql
        assert new_args == ()

    def test_apply_to_insert_auto_set(self) -> None:
        """Test INSERT with auto_set."""
        policy = AccessPolicy(auto_set={"tenant_id": ":tenant_id"})
        context = PolicyContextData(tenant_id="t123")
        values_data = [{"name": "Order 1", "amount": 100}]
        _, _, modified_values = self.enforcer.apply_to_insert(
            "", (), "orders", policy, context, values_data
        )
        assert modified_values[0]["tenant_id"] == "t123"
        assert modified_values[0]["name"] == "Order 1"

    def test_apply_to_insert_existing_value_not_overwritten(self) -> None:
        """Test INSERT doesn't overwrite existing values."""
        policy = AccessPolicy(auto_set={"tenant_id": ":tenant_id"})
        context = PolicyContextData(tenant_id="t123")
        values_data = [{"name": "Order 1", "tenant_id": "original"}]
        _, _, modified_values = self.enforcer.apply_to_insert(
            "", (), "orders", policy, context, values_data
        )
        assert modified_values[0]["tenant_id"] == "original"

    def test_apply_to_update_with_policy(self) -> None:
        """Test UPDATE with policy rules."""
        policy = AccessPolicy(update=["tenant_id = :tenant_id"])
        context = PolicyContextData(tenant_id="t123")
        sql = "UPDATE orders SET amount = $1"
        new_sql, new_args = self.enforcer.apply_to_update(
            sql, (100,), "orders", policy, context
        )
        assert "WHERE" in new_sql
        assert "(tenant_id = $2)" in new_sql
        assert new_args == (100, "t123")

    def test_apply_to_delete_with_policy(self) -> None:
        """Test DELETE with policy rules."""
        policy = AccessPolicy(delete=["tenant_id = :tenant_id", "user_id = :user_id"])
        context = PolicyContextData(tenant_id="t123", user_id="u456")
        sql = "DELETE FROM orders"
        new_sql, new_args = self.enforcer.apply_to_delete(
            sql, (), "orders", policy, context
        )
        assert "WHERE" in new_sql
        assert "(tenant_id = $1)" in new_sql
        assert "(user_id = $2)" in new_sql
        assert new_args == ("t123", "u456")


class TestGetEnforcer:
    """Tests for get_enforcer function."""

    def test_get_sqlite_enforcer(self) -> None:
        """Test getting SQLite enforcer."""
        enforcer = get_enforcer("sqlite")
        assert isinstance(enforcer, ApplicationLevelEnforcer)

    def test_get_mysql_enforcer(self) -> None:
        """Test getting MySQL enforcer."""
        enforcer = get_enforcer("mysql")
        assert isinstance(enforcer, ApplicationLevelEnforcer)

    def test_get_postgresql_enforcer(self) -> None:
        """Test getting PostgreSQL enforcer."""
        from pykour.db.access_policy import PostgreSQLNativeEnforcer

        enforcer = get_enforcer("postgresql")
        assert isinstance(enforcer, PostgreSQLNativeEnforcer)
