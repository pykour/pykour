"""Tests for SQL utility functions."""

from __future__ import annotations

from typing import Literal, cast

import pytest

from pykour.db.sql_utils import (
    InvalidIdentifierError,
    _MAX_IDENTIFIER_LENGTH,
    _SQL_RESERVED_KEYWORDS,
    is_valid_identifier,
    quote_identifier,
    validate_identifier,
    validate_rls_condition,
)

# Type alias for driver names
DriverName = Literal["sqlite", "postgresql", "mysql"]


class TestInvalidIdentifierError:
    """Tests for InvalidIdentifierError exception."""

    def test_basic_error_message(self) -> None:
        """Test basic error message without reason."""
        error = InvalidIdentifierError("123bad")
        assert error.identifier == "123bad"
        assert error.identifier_type == "identifier"
        assert "Invalid SQL identifier: '123bad'" in str(error)

    def test_error_with_identifier_type(self) -> None:
        """Test error message with custom identifier type."""
        error = InvalidIdentifierError("bad", "table")
        assert error.identifier_type == "table"
        assert "Invalid SQL table: 'bad'" in str(error)

    def test_error_with_reason(self) -> None:
        """Test error message with reason."""
        error = InvalidIdentifierError("123", "column", "must start with letter")
        assert error.reason == "must start with letter"
        assert "must start with letter" in str(error)

    def test_error_is_value_error(self) -> None:
        """Test that InvalidIdentifierError is a ValueError."""
        error = InvalidIdentifierError("bad")
        assert isinstance(error, ValueError)


class TestValidateIdentifier:
    """Tests for validate_identifier function."""

    def test_valid_simple_identifier(self) -> None:
        """Test validation of simple valid identifiers."""
        assert validate_identifier("users") == "users"
        assert validate_identifier("User") == "User"
        assert validate_identifier("USERS") == "USERS"

    def test_valid_identifier_with_underscore(self) -> None:
        """Test validation of identifiers with underscores."""
        assert validate_identifier("user_id") == "user_id"
        assert validate_identifier("_private") == "_private"
        assert validate_identifier("__double__") == "__double__"

    def test_valid_identifier_with_numbers(self) -> None:
        """Test validation of identifiers with numbers."""
        assert validate_identifier("user1") == "user1"
        assert validate_identifier("users123") == "users123"
        assert validate_identifier("table_1") == "table_1"

    def test_invalid_empty_identifier(self) -> None:
        """Test that empty identifier raises error."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_identifier("")
        assert "cannot be empty" in str(exc_info.value)

    def test_invalid_identifier_starts_with_number(self) -> None:
        """Test that identifier starting with number raises error."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_identifier("123users")
        assert "must start with letter or underscore" in str(exc_info.value)

    def test_invalid_identifier_with_special_chars(self) -> None:
        """Test that identifier with special characters raises error."""
        with pytest.raises(InvalidIdentifierError):
            validate_identifier("user-id")
        with pytest.raises(InvalidIdentifierError):
            validate_identifier("user.id")
        with pytest.raises(InvalidIdentifierError):
            validate_identifier("user@id")
        with pytest.raises(InvalidIdentifierError):
            validate_identifier("user id")

    def test_invalid_identifier_too_long(self) -> None:
        """Test that identifier exceeding max length raises error."""
        long_name = "a" * (_MAX_IDENTIFIER_LENGTH + 1)
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_identifier(long_name)
        assert "exceeds maximum length" in str(exc_info.value)

    def test_valid_identifier_at_max_length(self) -> None:
        """Test that identifier at max length is valid."""
        max_name = "a" * _MAX_IDENTIFIER_LENGTH
        assert validate_identifier(max_name) == max_name

    def test_reserved_keyword_raises_error(self) -> None:
        """Test that SQL reserved keywords raise error by default."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_identifier("select")
        assert "reserved keyword" in str(exc_info.value)

    def test_reserved_keyword_case_insensitive(self) -> None:
        """Test that reserved keyword check is case insensitive."""
        with pytest.raises(InvalidIdentifierError):
            validate_identifier("SELECT")
        with pytest.raises(InvalidIdentifierError):
            validate_identifier("Select")

    def test_reserved_keyword_allowed_with_flag(self) -> None:
        """Test that reserved keywords are allowed with allow_reserved=True."""
        assert validate_identifier("select", allow_reserved=True) == "select"
        assert validate_identifier("SELECT", allow_reserved=True) == "SELECT"

    def test_custom_identifier_type_in_error(self) -> None:
        """Test custom identifier type appears in error message."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_identifier("123bad", "table")
        assert "Invalid SQL table" in str(exc_info.value)

    @pytest.mark.parametrize(
        "keyword",
        [
            "select",
            "from",
            "where",
            "and",
            "or",
            "insert",
            "update",
            "delete",
            "create",
            "drop",
        ],
    )
    def test_common_reserved_keywords(self, keyword: str) -> None:
        """Test common SQL reserved keywords are rejected."""
        with pytest.raises(InvalidIdentifierError):
            validate_identifier(keyword)


class TestQuoteIdentifier:
    """Tests for quote_identifier function."""

    def test_quote_postgresql(self) -> None:
        """Test quoting for PostgreSQL."""
        assert quote_identifier("users", "postgresql") == '"users"'
        assert quote_identifier("user_id", "postgresql") == '"user_id"'

    def test_quote_sqlite(self) -> None:
        """Test quoting for SQLite."""
        assert quote_identifier("users", "sqlite") == '"users"'
        assert quote_identifier("user_id", "sqlite") == '"user_id"'

    def test_quote_mysql(self) -> None:
        """Test quoting for MySQL."""
        assert quote_identifier("users", "mysql") == "`users`"
        assert quote_identifier("user_id", "mysql") == "`user_id`"

    def test_escape_double_quotes_postgresql(self) -> None:
        """Test escaping double quotes in PostgreSQL/SQLite."""
        result = quote_identifier('user"name', "postgresql", validate=False)
        assert result == '"user""name"'

    def test_escape_backticks_mysql(self) -> None:
        """Test escaping backticks in MySQL."""
        result = quote_identifier("user`name", "mysql", validate=False)
        assert result == "`user``name`"

    def test_quote_with_validation_enabled(self) -> None:
        """Test that validation is applied by default."""
        with pytest.raises(InvalidIdentifierError):
            quote_identifier("123bad", "postgresql")

    def test_quote_without_validation(self) -> None:
        """Test quoting without validation."""
        result = quote_identifier("user name", "postgresql", validate=False)
        assert result == '"user name"'

    def test_quote_reserved_keyword_allowed(self) -> None:
        """Test that reserved keywords can be quoted."""
        assert quote_identifier("select", "postgresql") == '"select"'
        assert quote_identifier("from", "mysql") == "`from`"

    @pytest.mark.parametrize(
        "driver,expected_quote",
        [
            ("postgresql", '"'),
            ("sqlite", '"'),
            ("mysql", "`"),
        ],
    )
    def test_quote_character_by_driver(self, driver: str, expected_quote: str) -> None:
        """Test correct quote character is used for each driver."""
        result = quote_identifier("test", cast(DriverName, driver))
        assert result.startswith(expected_quote)
        assert result.endswith(expected_quote)


class TestIsValidIdentifier:
    """Tests for is_valid_identifier function."""

    def test_valid_identifiers_return_true(self) -> None:
        """Test that valid identifiers return True."""
        assert is_valid_identifier("users") is True
        assert is_valid_identifier("user_id") is True
        assert is_valid_identifier("_private") is True
        assert is_valid_identifier("table1") is True

    def test_invalid_identifiers_return_false(self) -> None:
        """Test that invalid identifiers return False."""
        assert is_valid_identifier("") is False
        assert is_valid_identifier("123bad") is False
        assert is_valid_identifier("user-id") is False
        assert is_valid_identifier("user.id") is False

    def test_reserved_keyword_returns_false(self) -> None:
        """Test that reserved keywords return False by default."""
        assert is_valid_identifier("select") is False
        assert is_valid_identifier("from") is False

    def test_reserved_keyword_allowed_returns_true(self) -> None:
        """Test that reserved keywords return True with allow_reserved=True."""
        assert is_valid_identifier("select", allow_reserved=True) is True
        assert is_valid_identifier("from", allow_reserved=True) is True

    def test_does_not_raise_exception(self) -> None:
        """Test that function never raises, always returns bool."""
        # These would raise if validate_identifier was called directly
        assert is_valid_identifier("") is False
        assert is_valid_identifier("a" * 1000) is False
        assert is_valid_identifier("123") is False


class TestValidateRLSCondition:
    """Tests for validate_rls_condition function."""

    def test_valid_simple_condition(self) -> None:
        """Test valid simple RLS conditions."""
        assert (
            validate_rls_condition("user_id = :current_user")
            == "user_id = :current_user"
        )
        assert validate_rls_condition("tenant_id = :tenant") == "tenant_id = :tenant"

    def test_valid_complex_condition(self) -> None:
        """Test valid complex RLS conditions."""
        cond = "user_id = :user AND status = 'active'"
        assert validate_rls_condition(cond) == cond

    def test_valid_comparison_operators(self) -> None:
        """Test valid conditions with various comparison operators."""
        assert validate_rls_condition("age >= :min_age") == "age >= :min_age"
        assert validate_rls_condition("price < :max_price") == "price < :max_price"
        assert validate_rls_condition("name != :excluded") == "name != :excluded"

    def test_empty_condition_raises_error(self) -> None:
        """Test that empty condition raises error."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_rls_condition("")
        assert "cannot be empty" in str(exc_info.value)

    def test_semicolon_injection_blocked(self) -> None:
        """Test that semicolon injection is blocked."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_rls_condition("user_id = 1; DROP TABLE users")
        assert "semicolons are not allowed" in str(exc_info.value)

    def test_sql_comment_dash_blocked(self) -> None:
        """Test that SQL comment (--) is blocked."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_rls_condition("user_id = 1 -- comment")
        assert "comments are not allowed" in str(exc_info.value)

    def test_sql_comment_block_blocked(self) -> None:
        """Test that SQL block comment (/* */) is blocked."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_rls_condition("user_id = 1 /* comment */")
        assert "comments are not allowed" in str(exc_info.value)

    def test_union_injection_blocked(self) -> None:
        """Test that UNION injection is blocked."""
        with pytest.raises(InvalidIdentifierError) as exc_info:
            validate_rls_condition("user_id = 1 UNION SELECT * FROM passwords")
        assert "UNION is not allowed" in str(exc_info.value)

    def test_exec_injection_blocked(self) -> None:
        """Test that EXEC injection is blocked."""
        with pytest.raises(InvalidIdentifierError):
            validate_rls_condition("user_id = 1 exec xp_cmdshell")
        with pytest.raises(InvalidIdentifierError):
            validate_rls_condition("user_id = 1 execute xp_cmdshell")

    @pytest.mark.parametrize(
        "dangerous_keyword",
        [
            "drop",
            "truncate",
            "delete",
            "insert",
            "update",
            "create",
            "alter",
            "grant",
            "revoke",
        ],
    )
    def test_dangerous_keywords_blocked(self, dangerous_keyword: str) -> None:
        """Test that dangerous SQL keywords are blocked."""
        with pytest.raises(InvalidIdentifierError):
            validate_rls_condition(f"user_id = 1 {dangerous_keyword} table users")

    def test_case_insensitive_blocking(self) -> None:
        """Test that dangerous patterns are blocked case insensitively."""
        with pytest.raises(InvalidIdentifierError):
            validate_rls_condition("user_id = 1 DROP TABLE users")
        with pytest.raises(InvalidIdentifierError):
            validate_rls_condition("user_id = 1 Drop Table users")

    def test_word_boundary_matching(self) -> None:
        """Test that only whole words are matched for dangerous patterns."""
        # 'updated_at' contains 'update' but should be allowed since it's not a whole word
        assert validate_rls_condition("updated_at = :now") == "updated_at = :now"
        # 'dropdown' contains 'drop' but should be allowed
        assert validate_rls_condition("dropdown_id = :id") == "dropdown_id = :id"


class TestReservedKeywords:
    """Tests for SQL reserved keywords set."""

    def test_keywords_are_lowercase(self) -> None:
        """Test that all reserved keywords are lowercase."""
        for keyword in _SQL_RESERVED_KEYWORDS:
            assert keyword == keyword.lower(), f"Keyword '{keyword}' is not lowercase"

    def test_common_keywords_present(self) -> None:
        """Test that common SQL keywords are in the set."""
        common_keywords = [
            "select",
            "from",
            "where",
            "and",
            "or",
            "not",
            "insert",
            "update",
            "delete",
            "create",
            "drop",
            "table",
            "index",
            "join",
            "left",
            "right",
            "inner",
            "outer",
            "group",
            "order",
            "by",
            "having",
            "limit",
            "offset",
        ]
        for keyword in common_keywords:
            assert keyword in _SQL_RESERVED_KEYWORDS, f"Missing keyword: {keyword}"

    def test_keywords_frozenset_immutable(self) -> None:
        """Test that reserved keywords cannot be modified."""
        assert isinstance(_SQL_RESERVED_KEYWORDS, frozenset)
