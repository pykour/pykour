"""Tests for environment variable expansion in configuration."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock


from pykour.config.loader import (
    expand_env_vars,
    expand_env_vars_recursive,
    load_toml,
)


class TestExpandEnvVars:
    """Tests for expand_env_vars function."""

    def test_simple_variable(self) -> None:
        """Test expanding a simple variable."""
        with mock.patch.dict(os.environ, {"MY_VAR": "hello"}):
            result = expand_env_vars("${MY_VAR}")
            assert result == "hello"

    def test_variable_with_surrounding_text(self) -> None:
        """Test expanding a variable with surrounding text."""
        with mock.patch.dict(os.environ, {"DB_HOST": "localhost"}):
            result = expand_env_vars("postgres://${DB_HOST}:5432/db")
            assert result == "postgres://localhost:5432/db"

    def test_multiple_variables(self) -> None:
        """Test expanding multiple variables."""
        with mock.patch.dict(os.environ, {"HOST": "localhost", "PORT": "5432"}):
            result = expand_env_vars("${HOST}:${PORT}")
            assert result == "localhost:5432"

    def test_variable_not_set_returns_empty(self) -> None:
        """Test that unset variable returns empty string."""
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("UNDEFINED_VAR", None)
            result = expand_env_vars("prefix_${UNDEFINED_VAR}_suffix")
            assert result == "prefix__suffix"

    def test_variable_with_default(self) -> None:
        """Test variable with default value when not set."""
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MY_VAR", None)
            result = expand_env_vars("${MY_VAR:-default_value}")
            assert result == "default_value"

    def test_variable_with_default_when_set(self) -> None:
        """Test variable with default value when variable is set."""
        with mock.patch.dict(os.environ, {"MY_VAR": "actual_value"}):
            result = expand_env_vars("${MY_VAR:-default_value}")
            assert result == "actual_value"

    def test_empty_default(self) -> None:
        """Test variable with empty default."""
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MY_VAR", None)
            result = expand_env_vars("${MY_VAR:-}")
            assert result == ""

    def test_no_variables(self) -> None:
        """Test string with no variables."""
        result = expand_env_vars("plain text")
        assert result == "plain text"

    def test_dollar_sign_without_braces(self) -> None:
        """Test that $VAR without braces is not expanded."""
        result = expand_env_vars("$MY_VAR")
        assert result == "$MY_VAR"

    def test_underscore_in_variable_name(self) -> None:
        """Test variable names with underscores."""
        with mock.patch.dict(os.environ, {"MY_LONG_VAR_NAME": "value"}):
            result = expand_env_vars("${MY_LONG_VAR_NAME}")
            assert result == "value"

    def test_numbers_in_variable_name(self) -> None:
        """Test variable names with numbers."""
        with mock.patch.dict(os.environ, {"VAR123": "value"}):
            result = expand_env_vars("${VAR123}")
            assert result == "value"


class TestExpandEnvVarsRecursive:
    """Tests for expand_env_vars_recursive function."""

    def test_string(self) -> None:
        """Test expanding a string."""
        with mock.patch.dict(os.environ, {"VAR": "value"}):
            result = expand_env_vars_recursive("${VAR}")
            assert result == "value"

    def test_dict(self) -> None:
        """Test expanding a dictionary."""
        with mock.patch.dict(os.environ, {"HOST": "localhost", "PORT": "5432"}):
            data = {
                "host": "${HOST}",
                "port": "${PORT}",
                "name": "mydb",
            }
            result = expand_env_vars_recursive(data)
            assert result == {
                "host": "localhost",
                "port": "5432",
                "name": "mydb",
            }

    def test_nested_dict(self) -> None:
        """Test expanding a nested dictionary."""
        with mock.patch.dict(os.environ, {"SECRET": "mysecret"}):
            data = {
                "database": {
                    "connection": {
                        "password": "${SECRET}",
                    }
                }
            }
            result = expand_env_vars_recursive(data)
            assert result["database"]["connection"]["password"] == "mysecret"

    def test_list(self) -> None:
        """Test expanding a list."""
        with mock.patch.dict(
            os.environ, {"ORIGIN1": "http://a.com", "ORIGIN2": "http://b.com"}
        ):
            data = ["${ORIGIN1}", "${ORIGIN2}", "http://c.com"]
            result = expand_env_vars_recursive(data)
            assert result == ["http://a.com", "http://b.com", "http://c.com"]

    def test_list_in_dict(self) -> None:
        """Test expanding a list inside a dictionary."""
        with mock.patch.dict(os.environ, {"ORIGIN": "http://example.com"}):
            data = {"cors": {"allow_origins": ["${ORIGIN}", "http://other.com"]}}
            result = expand_env_vars_recursive(data)
            assert result["cors"]["allow_origins"] == [
                "http://example.com",
                "http://other.com",
            ]

    def test_non_string_values_unchanged(self) -> None:
        """Test that non-string values are unchanged."""
        data = {
            "count": 42,
            "enabled": True,
            "ratio": 3.14,
            "nothing": None,
        }
        result = expand_env_vars_recursive(data)
        assert result == data


class TestLoadTomlWithEnvExpansion:
    """Tests for load_toml with environment variable expansion."""

    def test_load_toml_expands_env_vars(self) -> None:
        """Test that load_toml expands environment variables."""
        toml_content = b"""
[database]
url = "${DATABASE_URL}"

[app]
name = "myapp"
"""
        with mock.patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
            with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
                f.write(toml_content)
                f.flush()
                try:
                    result = load_toml(Path(f.name))
                    assert result["database"]["url"] == "sqlite:///test.db"
                    assert result["app"]["name"] == "myapp"
                finally:
                    os.unlink(f.name)

    def test_load_toml_with_default_values(self) -> None:
        """Test that load_toml handles default values."""
        toml_content = b"""
[database]
url = "${DATABASE_URL:-sqlite:///default.db}"
"""
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABASE_URL", None)
            with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
                f.write(toml_content)
                f.flush()
                try:
                    result = load_toml(Path(f.name))
                    assert result["database"]["url"] == "sqlite:///default.db"
                finally:
                    os.unlink(f.name)

    def test_load_toml_without_expansion(self) -> None:
        """Test that load_toml can skip expansion."""
        toml_content = b"""
[database]
url = "${DATABASE_URL}"
"""
        with mock.patch.dict(os.environ, {"DATABASE_URL": "sqlite:///test.db"}):
            with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
                f.write(toml_content)
                f.flush()
                try:
                    result = load_toml(Path(f.name), expand_env=False)
                    assert result["database"]["url"] == "${DATABASE_URL}"
                finally:
                    os.unlink(f.name)
