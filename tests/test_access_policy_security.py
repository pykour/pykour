"""Tests for access policy security fixes (SQL injection prevention)."""

import pytest

from pykour.db.access_policy.enforcer import (
    PostgreSQLNativeEnforcer,
    _VALID_KEY_PATTERN,
)


class TestKeyValidation:
    """Tests for custom context key validation."""

    def test_valid_key_simple(self) -> None:
        """Simple alphanumeric keys should be valid."""
        assert _VALID_KEY_PATTERN.match("tenant_id")
        assert _VALID_KEY_PATTERN.match("user")
        assert _VALID_KEY_PATTERN.match("organization_id")

    def test_valid_key_underscore_prefix(self) -> None:
        """Keys starting with underscore should be valid."""
        assert _VALID_KEY_PATTERN.match("_private")
        assert _VALID_KEY_PATTERN.match("_internal_key")

    def test_valid_key_with_numbers(self) -> None:
        """Keys containing numbers (not leading) should be valid."""
        assert _VALID_KEY_PATTERN.match("user2")
        assert _VALID_KEY_PATTERN.match("tenant_v2_id")

    def test_invalid_key_starts_with_number(self) -> None:
        """Keys starting with numbers should be invalid."""
        assert not _VALID_KEY_PATTERN.match("1user")
        assert not _VALID_KEY_PATTERN.match("123key")

    def test_invalid_key_special_chars(self) -> None:
        """Keys with special characters should be invalid."""
        assert not _VALID_KEY_PATTERN.match("user-id")
        assert not _VALID_KEY_PATTERN.match("tenant.id")
        assert not _VALID_KEY_PATTERN.match("key@name")

    def test_invalid_key_sql_injection_attempts(self) -> None:
        """SQL injection attempts in key names should be invalid."""
        # Attempting to break out of config name
        assert not _VALID_KEY_PATTERN.match("foo', $1, false); DROP TABLE users; --")
        assert not _VALID_KEY_PATTERN.match("foo'; --")
        assert not _VALID_KEY_PATTERN.match("key; SELECT 1")

    def test_invalid_key_empty_string(self) -> None:
        """Empty string should be invalid."""
        assert not _VALID_KEY_PATTERN.match("")

    def test_invalid_key_whitespace(self) -> None:
        """Keys with whitespace should be invalid."""
        assert not _VALID_KEY_PATTERN.match("key name")
        assert not _VALID_KEY_PATTERN.match(" key")
        assert not _VALID_KEY_PATTERN.match("key ")


class TestPostgreSQLNativeEnforcer:
    """Tests for PostgreSQLNativeEnforcer security."""

    def test_validate_key_name_valid(self) -> None:
        """Valid key names should pass validation."""
        enforcer = PostgreSQLNativeEnforcer()
        assert enforcer._validate_key_name("tenant_id") is True
        assert enforcer._validate_key_name("user") is True
        assert enforcer._validate_key_name("_private") is True
        assert enforcer._validate_key_name("CamelCase") is True

    def test_validate_key_name_invalid(self) -> None:
        """Invalid key names should fail validation."""
        enforcer = PostgreSQLNativeEnforcer()
        assert enforcer._validate_key_name("1invalid") is False
        assert enforcer._validate_key_name("has-dash") is False
        assert enforcer._validate_key_name("has.dot") is False
        assert enforcer._validate_key_name("") is False


class TestMockedSetupConnection:
    """Tests for setup_connection with mocked database connection."""

    @pytest.mark.asyncio
    async def test_setup_connection_uses_parameterized_queries(self) -> None:
        """Verify that setup_connection uses parameterized queries."""
        from unittest.mock import AsyncMock

        from pykour.db.access_policy.context import PolicyContextData

        mock_conn = AsyncMock()
        enforcer = PostgreSQLNativeEnforcer()

        context = PolicyContextData(
            tenant_id="tenant-123",
            user_id="user-456",
        )

        await enforcer.setup_connection(mock_conn, context)

        # Verify set_config is used with parameters
        calls = mock_conn.execute.call_args_list
        assert len(calls) >= 3

        # Check tenant_id call uses parameterized query
        tenant_call = calls[0]
        assert "set_config" in tenant_call.args[0]
        assert "$1" in tenant_call.args[0]
        assert tenant_call.args[1] == "tenant-123"

        # Check user_id call uses parameterized query
        user_call = calls[1]
        assert "set_config" in user_call.args[0]
        assert "$1" in user_call.args[0]
        assert user_call.args[1] == "user-456"

    @pytest.mark.asyncio
    async def test_setup_connection_escapes_malicious_values(self) -> None:
        """Values with SQL injection attempts should be safely parameterized."""
        from unittest.mock import AsyncMock

        from pykour.db.access_policy.context import PolicyContextData

        mock_conn = AsyncMock()
        enforcer = PostgreSQLNativeEnforcer()

        # Attempt SQL injection through context values
        context = PolicyContextData(
            tenant_id="'; DROP TABLE users; --",
            user_id="user' OR '1'='1",
        )

        await enforcer.setup_connection(mock_conn, context)

        calls = mock_conn.execute.call_args_list

        # The malicious values should be passed as parameters, not interpolated
        tenant_call = calls[0]
        assert tenant_call.args[1] == "'; DROP TABLE users; --"
        # The SQL should not contain the malicious string directly
        assert "DROP TABLE" not in tenant_call.args[0]

    @pytest.mark.asyncio
    async def test_setup_connection_rejects_invalid_custom_keys(self) -> None:
        """Custom context keys with invalid names should raise ValueError."""
        from unittest.mock import AsyncMock

        from pykour.db.access_policy.context import PolicyContextData

        mock_conn = AsyncMock()
        enforcer = PostgreSQLNativeEnforcer()

        context = PolicyContextData(
            tenant_id="tenant-123",
            custom={"valid_key": "value", "invalid-key": "value"},
        )

        with pytest.raises(ValueError, match="Invalid custom context key name"):
            await enforcer.setup_connection(mock_conn, context)

    @pytest.mark.asyncio
    async def test_setup_connection_accepts_valid_custom_keys(self) -> None:
        """Custom context keys with valid names should work."""
        from unittest.mock import AsyncMock

        from pykour.db.access_policy.context import PolicyContextData

        mock_conn = AsyncMock()
        enforcer = PostgreSQLNativeEnforcer()

        context = PolicyContextData(
            tenant_id="tenant-123",
            custom={"department_id": "sales", "region_code": "US"},
        )

        # Should not raise
        await enforcer.setup_connection(mock_conn, context)

        # Verify custom keys are set with parameterized queries
        calls = mock_conn.execute.call_args_list

        # Find calls for custom keys
        custom_calls = [
            c
            for c in calls
            if "department_id" in c.args[0] or "region_code" in c.args[0]
        ]
        assert len(custom_calls) == 2

        for call in custom_calls:
            assert "$1" in call.args[0]

    @pytest.mark.asyncio
    async def test_setup_connection_handles_none_values(self) -> None:
        """None values should be converted to empty strings."""
        from unittest.mock import AsyncMock

        from pykour.db.access_policy.context import PolicyContextData

        mock_conn = AsyncMock()
        enforcer = PostgreSQLNativeEnforcer()

        context = PolicyContextData(
            tenant_id=None,
            user_id=None,
            organization_id=None,
        )

        await enforcer.setup_connection(mock_conn, context)

        calls = mock_conn.execute.call_args_list

        # All standard values should be empty strings
        assert calls[0].args[1] == ""
        assert calls[1].args[1] == ""
        assert calls[2].args[1] == ""
