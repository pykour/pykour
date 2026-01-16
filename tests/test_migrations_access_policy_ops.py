"""Tests for access policy migration operations."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pykour.db.migrations.access_policy_ops import (
    AlterAccessPolicy,
    CreateAccessPolicy,
    DropAccessPolicy,
)
from pykour.db.sql_utils import InvalidIdentifierError


def create_mock_driver(driver_name: str = "sqlite") -> MagicMock:
    """Create a mock driver for testing."""
    driver = MagicMock()
    driver.driver_name = driver_name
    driver.execute = AsyncMock()
    driver.fetch_all = AsyncMock(return_value=[])
    driver.fetch_one = AsyncMock(return_value=None)
    driver.convert_placeholders = MagicMock(side_effect=lambda sql, _: sql.replace("$1", "?").replace("$2", "?"))
    return driver


class TestCreateAccessPolicy:
    """Tests for CreateAccessPolicy operation."""

    def test_to_code_basic(self) -> None:
        """Test to_code generates correct Python code."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
        )
        code = op.to_code()
        assert 'op.create_access_policy("orders", "orders_tenant")' == code

    def test_to_code_with_select(self) -> None:
        """Test to_code includes select rules."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            select=["tenant_id = :tenant_id"],
        )
        code = op.to_code()
        assert '"orders"' in code
        assert "select=" in code
        assert "tenant_id = :tenant_id" in code

    def test_to_code_with_all_options(self) -> None:
        """Test to_code includes all options."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            select=["tenant_id = :tenant_id"],
            insert=["tenant_id = :tenant_id"],
            update=["tenant_id = :tenant_id"],
            delete=["tenant_id = :tenant_id"],
            auto_set={"tenant_id": ":tenant_id"},
            bypass_roles=["admin"],
        )
        code = op.to_code()
        assert "select=" in code
        assert "insert=" in code
        assert "update=" in code
        assert "delete=" in code
        assert "auto_set=" in code
        assert "bypass_roles=" in code

    def test_reverse_creates_drop_policy(self) -> None:
        """Test reverse returns DropAccessPolicy."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            select=["tenant_id = :tenant_id"],
        )
        reverse = op.reverse()

        assert isinstance(reverse, DropAccessPolicy)
        assert reverse.table == "orders"
        assert reverse.policy_name == "orders_tenant"
        assert reverse._policy_backup is not None
        assert reverse._policy_backup["select"] == ["tenant_id = :tenant_id"]

    @pytest.mark.asyncio
    async def test_execute_validates_table_name(self) -> None:
        """Test execute validates table name."""
        op = CreateAccessPolicy(
            table="123invalid",
            policy_name="policy",
        )
        driver = create_mock_driver()
        conn = MagicMock()

        with pytest.raises(InvalidIdentifierError):
            await op.execute(driver, conn)

    @pytest.mark.asyncio
    async def test_execute_validates_policy_name(self) -> None:
        """Test execute validates policy name."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="invalid;policy",
        )
        driver = create_mock_driver()
        conn = MagicMock()

        with pytest.raises(InvalidIdentifierError):
            await op.execute(driver, conn)

    @pytest.mark.asyncio
    async def test_execute_validates_rls_conditions(self) -> None:
        """Test execute validates RLS conditions."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="policy",
            select=["tenant_id = 1; DROP TABLE users"],  # SQL injection
        )
        driver = create_mock_driver()
        conn = MagicMock()

        with pytest.raises(InvalidIdentifierError):
            await op.execute(driver, conn)

    @pytest.mark.asyncio
    async def test_execute_postgresql_enables_rls(self) -> None:
        """Test execute enables RLS for PostgreSQL."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            select=["tenant_id = :tenant_id"],
        )
        driver = create_mock_driver("postgresql")
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that ALTER TABLE ENABLE ROW LEVEL SECURITY was called
        calls = [str(call) for call in driver.execute.call_args_list]
        assert any("ENABLE ROW LEVEL SECURITY" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_execute_postgresql_creates_policies(self) -> None:
        """Test execute creates PostgreSQL policies."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            select=["tenant_id = :tenant_id"],
            insert=["tenant_id = :tenant_id"],
        )
        driver = create_mock_driver("postgresql")
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that CREATE POLICY was called with correct actions
        calls = [str(call) for call in driver.execute.call_args_list]
        assert any("CREATE POLICY" in str(call) and "SELECT" in str(call) for call in calls)
        assert any("CREATE POLICY" in str(call) and "INSERT" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_execute_postgresql_converts_params(self) -> None:
        """Test execute converts :param to current_setting()."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            select=["tenant_id = :tenant_id"],
        )
        driver = create_mock_driver("postgresql")
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that current_setting was used
        calls = [str(call) for call in driver.execute.call_args_list]
        assert any("current_setting('app.tenant_id'" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_execute_sqlite_stores_metadata(self) -> None:
        """Test execute stores policy in metadata table for SQLite."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            select=["tenant_id = :tenant_id"],
        )
        driver = create_mock_driver("sqlite")
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that metadata table was created and policy was inserted
        calls = [str(call) for call in driver.execute.call_args_list]
        assert any("CREATE TABLE IF NOT EXISTS _pykour_access_policies" in str(call) for call in calls)
        assert any("INSERT INTO _pykour_access_policies" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_execute_mysql_stores_metadata(self) -> None:
        """Test execute stores policy in metadata table for MySQL."""
        op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            select=["tenant_id = :tenant_id"],
        )
        driver = create_mock_driver("mysql")
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that MySQL-specific table was created
        calls = [str(call) for call in driver.execute.call_args_list]
        assert any("AUTO_INCREMENT" in str(call) for call in calls)

    def test_convert_to_pg_condition_single(self) -> None:
        """Test _convert_to_pg_condition with single condition."""
        op = CreateAccessPolicy("orders", "policy")
        result = op._convert_to_pg_condition(["tenant_id = :tenant_id"])
        assert result == "(tenant_id = current_setting('app.tenant_id', true))"

    def test_convert_to_pg_condition_multiple(self) -> None:
        """Test _convert_to_pg_condition with multiple conditions."""
        op = CreateAccessPolicy("orders", "policy")
        result = op._convert_to_pg_condition(["tenant_id = :tenant_id", "user_id = :user_id"])
        assert "AND" in result
        assert "app.tenant_id" in result
        assert "app.user_id" in result


class TestDropAccessPolicy:
    """Tests for DropAccessPolicy operation."""

    def test_to_code(self) -> None:
        """Test to_code generates correct Python code."""
        op = DropAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
        )
        code = op.to_code()
        assert 'op.drop_access_policy("orders", "orders_tenant")' == code

    def test_reverse_without_backup_raises(self) -> None:
        """Test reverse raises error without backup."""
        op = DropAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
        )
        with pytest.raises(ValueError) as exc_info:
            op.reverse()
        assert "Cannot reverse DropAccessPolicy without backup" in str(exc_info.value)

    def test_reverse_with_backup_creates_create_policy(self) -> None:
        """Test reverse creates CreateAccessPolicy with backup data."""
        op = DropAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            _policy_backup={
                "select": ["tenant_id = :tenant_id"],
                "insert": ["tenant_id = :tenant_id"],
                "update": [],
                "delete": [],
                "auto_set": {},
                "bypass_roles": [],
            },
        )
        reverse = op.reverse()

        assert isinstance(reverse, CreateAccessPolicy)
        assert reverse.table == "orders"
        assert reverse.policy_name == "orders_tenant"
        assert reverse.select == ["tenant_id = :tenant_id"]
        assert reverse.insert == ["tenant_id = :tenant_id"]

    @pytest.mark.asyncio
    async def test_execute_validates_table_name(self) -> None:
        """Test execute validates table name."""
        op = DropAccessPolicy(
            table="123invalid",
            policy_name="policy",
        )
        driver = create_mock_driver()
        conn = MagicMock()

        with pytest.raises(InvalidIdentifierError):
            await op.execute(driver, conn)

    @pytest.mark.asyncio
    async def test_execute_postgresql_drops_policies(self) -> None:
        """Test execute drops PostgreSQL policies."""
        op = DropAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
        )
        driver = create_mock_driver("postgresql")
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that DROP POLICY was called for each action
        calls = [str(call) for call in driver.execute.call_args_list]
        assert any("DROP POLICY IF EXISTS orders_tenant_select" in str(call) for call in calls)
        assert any("DROP POLICY IF EXISTS orders_tenant_insert" in str(call) for call in calls)
        assert any("DROP POLICY IF EXISTS orders_tenant_update" in str(call) for call in calls)
        assert any("DROP POLICY IF EXISTS orders_tenant_delete" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_execute_postgresql_disables_rls(self) -> None:
        """Test execute attempts to disable RLS for PostgreSQL."""
        op = DropAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
        )
        driver = create_mock_driver("postgresql")
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that DISABLE ROW LEVEL SECURITY was attempted
        calls = [str(call) for call in driver.execute.call_args_list]
        assert any("DISABLE ROW LEVEL SECURITY" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_execute_sqlite_removes_metadata(self) -> None:
        """Test execute removes policy from metadata table for SQLite."""
        op = DropAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
        )
        driver = create_mock_driver("sqlite")
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that DELETE was called
        calls = [str(call) for call in driver.execute.call_args_list]
        assert any("DELETE FROM _pykour_access_policies" in str(call) for call in calls)


class TestAlterAccessPolicy:
    """Tests for AlterAccessPolicy operation."""

    def test_to_code_basic(self) -> None:
        """Test to_code generates correct Python code."""
        op = AlterAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
        )
        code = op.to_code()
        assert 'op.alter_access_policy("orders", "orders_tenant")' == code

    def test_to_code_with_new_select(self) -> None:
        """Test to_code includes new_select."""
        op = AlterAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            new_select=["tenant_id = :tenant_id", "active = true"],
        )
        code = op.to_code()
        assert "new_select=" in code
        assert "active = true" in code

    def test_to_code_with_all_options(self) -> None:
        """Test to_code includes all new options."""
        op = AlterAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            new_select=["tenant_id = :tenant_id"],
            new_insert=["tenant_id = :tenant_id"],
            new_update=["tenant_id = :tenant_id"],
            new_delete=["tenant_id = :tenant_id"],
            new_auto_set={"tenant_id": ":tenant_id"},
            new_bypass_roles=["admin"],
        )
        code = op.to_code()
        assert "new_select=" in code
        assert "new_insert=" in code
        assert "new_update=" in code
        assert "new_delete=" in code
        assert "new_auto_set=" in code
        assert "new_bypass_roles=" in code

    def test_reverse_without_backup_raises(self) -> None:
        """Test reverse raises error without old_policy."""
        op = AlterAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            new_select=["tenant_id = :tenant_id"],
        )
        with pytest.raises(ValueError) as exc_info:
            op.reverse()
        assert "Cannot reverse AlterAccessPolicy without backup" in str(exc_info.value)

    def test_reverse_with_backup(self) -> None:
        """Test reverse creates AlterAccessPolicy with old values."""
        op = AlterAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            new_select=["tenant_id = :tenant_id", "active = true"],
            _old_policy={
                "select": ["tenant_id = :tenant_id"],
                "insert": [],
                "update": [],
                "delete": [],
                "auto_set": {},
                "bypass_roles": [],
            },
        )
        reverse = op.reverse()

        assert isinstance(reverse, AlterAccessPolicy)
        assert reverse.table == "orders"
        assert reverse.new_select == ["tenant_id = :tenant_id"]

    @pytest.mark.asyncio
    async def test_execute_validates_table_name(self) -> None:
        """Test execute validates table name."""
        op = AlterAccessPolicy(
            table="123invalid",
            policy_name="policy",
        )
        driver = create_mock_driver()
        conn = MagicMock()

        with pytest.raises(InvalidIdentifierError):
            await op.execute(driver, conn)

    @pytest.mark.asyncio
    async def test_execute_validates_new_conditions(self) -> None:
        """Test execute validates new RLS conditions."""
        op = AlterAccessPolicy(
            table="orders",
            policy_name="policy",
            new_select=["tenant_id = 1; DROP TABLE users"],  # SQL injection
        )
        driver = create_mock_driver()
        conn = MagicMock()

        with pytest.raises(InvalidIdentifierError):
            await op.execute(driver, conn)

    @pytest.mark.asyncio
    async def test_execute_sqlite_drops_and_recreates(self) -> None:
        """Test execute drops old policy and creates new one."""
        op = AlterAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            new_select=["tenant_id = :tenant_id", "active = true"],
        )
        driver = create_mock_driver("sqlite")
        # Return existing policy data
        driver.fetch_all = AsyncMock(return_value=[{
            "select_rules": '["tenant_id = :tenant_id"]',
            "insert_rules": '[]',
            "update_rules": '[]',
            "delete_rules": '[]',
            "auto_set": '{}',
            "bypass_roles": '[]',
        }])
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that DELETE and INSERT were called
        calls = [str(call) for call in driver.execute.call_args_list]
        assert any("DELETE" in str(call) for call in calls)
        assert any("INSERT" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_execute_postgresql_queries_pg_policies(self) -> None:
        """Test execute queries pg_policies for current policy."""
        op = AlterAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            new_select=["tenant_id = :tenant_id", "active = true"],
        )
        driver = create_mock_driver("postgresql")
        # Return policy data from pg_policies
        driver.fetch_all = AsyncMock(return_value=[
            {"policyname": "orders_tenant_select", "qual": "current_setting('app.tenant_id', true)", "with_check": None},
        ])
        conn = MagicMock()

        await op.execute(driver, conn)

        # Check that pg_policies was queried
        first_call = driver.fetch_all.call_args_list[0]
        assert "pg_policies" in str(first_call)

    def test_convert_from_pg_condition(self) -> None:
        """Test _convert_from_pg_condition converts back to :param."""
        op = AlterAccessPolicy("orders", "policy")
        result = op._convert_from_pg_condition(
            "current_setting('app.tenant_id', true)"
        )
        assert result == ":tenant_id"

    def test_convert_from_pg_condition_without_true(self) -> None:
        """Test _convert_from_pg_condition handles case without true arg."""
        op = AlterAccessPolicy("orders", "policy")
        result = op._convert_from_pg_condition(
            "current_setting('app.tenant_id')"
        )
        assert result == ":tenant_id"


class TestAccessPolicyIntegration:
    """Integration tests for access policy operations."""

    def test_create_reverse_drop(self) -> None:
        """Test CreateAccessPolicy reverse is DropAccessPolicy that can reverse back."""
        create_op = CreateAccessPolicy(
            table="orders",
            policy_name="orders_tenant",
            select=["tenant_id = :tenant_id"],
            insert=["tenant_id = :tenant_id"],
            auto_set={"tenant_id": ":tenant_id"},
        )

        # Create -> Drop
        drop_op = create_op.reverse()
        assert isinstance(drop_op, DropAccessPolicy)

        # Drop -> Create (restore)
        restore_op = drop_op.reverse()
        assert isinstance(restore_op, CreateAccessPolicy)
        assert restore_op.table == "orders"
        assert restore_op.policy_name == "orders_tenant"
        assert restore_op.select == ["tenant_id = :tenant_id"]
        assert restore_op.insert == ["tenant_id = :tenant_id"]
        assert restore_op.auto_set == {"tenant_id": ":tenant_id"}
