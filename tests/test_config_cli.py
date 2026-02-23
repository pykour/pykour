"""Tests for CLI configuration utilities."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path
from unittest import mock


from pykour.config.cli import (
    get_config_value,
    get_database_url_from_config,
)
from pykour.config.models import PykourConfig


class TestGetDatabaseUrlFromConfig:
    """Tests for get_database_url_from_config function."""

    def test_cli_flag_highest_priority(self) -> None:
        """Test that CLI flag has highest priority."""
        args = argparse.Namespace(database="sqlite:///cli.db")
        config = PykourConfig()
        config.database.url = "sqlite:///config.db"

        with mock.patch.dict(os.environ, {"PYKOUR_DATABASE_URL": "sqlite:///env.db"}):
            result = get_database_url_from_config(args, config)
            assert result == "sqlite:///cli.db"

    def test_env_var_second_priority(self) -> None:
        """Test that environment variable has second priority."""
        args = argparse.Namespace(database=None)
        config = PykourConfig()
        config.database.url = "sqlite:///config.db"

        with mock.patch.dict(os.environ, {"PYKOUR_DATABASE_URL": "sqlite:///env.db"}):
            result = get_database_url_from_config(args, config)
            assert result == "sqlite:///env.db"

    def test_config_file_third_priority(self) -> None:
        """Test that config file has third priority."""
        args = argparse.Namespace(database=None)
        config = PykourConfig()
        config.database.url = "sqlite:///config.db"

        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PYKOUR_DATABASE_URL", None)
            result = get_database_url_from_config(args, config)
            assert result == "sqlite:///config.db"

    def test_returns_none_when_not_configured(self) -> None:
        """Test that None is returned when no database URL is configured."""
        args = argparse.Namespace(database=None)
        config = PykourConfig()
        config.database.url = None

        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PYKOUR_DATABASE_URL", None)
            result = get_database_url_from_config(args, config)
            assert result is None

    def test_empty_cli_flag_uses_next_priority(self) -> None:
        """Test that empty CLI flag falls through to next priority."""
        args = argparse.Namespace(database="")
        config = PykourConfig()
        config.database.url = "sqlite:///config.db"

        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PYKOUR_DATABASE_URL", None)
            result = get_database_url_from_config(args, config)
            assert result == "sqlite:///config.db"

    def test_none_args(self) -> None:
        """Test with None args."""
        config = PykourConfig()
        config.database.url = "sqlite:///config.db"

        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("PYKOUR_DATABASE_URL", None)
            result = get_database_url_from_config(None, config)
            assert result == "sqlite:///config.db"


class TestGetConfigValue:
    """Tests for get_config_value function."""

    def test_cli_flag_highest_priority(self) -> None:
        """Test that CLI flag has highest priority."""
        args = argparse.Namespace(my_value="from_cli")
        config = PykourConfig()

        with mock.patch.dict(os.environ, {"MY_ENV_VAR": "from_env"}):
            result = get_config_value(
                key="test",
                args=args,
                args_attr="my_value",
                env_var="MY_ENV_VAR",
                config=config,
                config_getter=lambda c: "from_config",
                default="from_default",
            )
            assert result == "from_cli"

    def test_env_var_second_priority(self) -> None:
        """Test that environment variable has second priority."""
        args = argparse.Namespace(my_value=None)
        config = PykourConfig()

        with mock.patch.dict(os.environ, {"MY_ENV_VAR": "from_env"}):
            result = get_config_value(
                key="test",
                args=args,
                args_attr="my_value",
                env_var="MY_ENV_VAR",
                config=config,
                config_getter=lambda c: "from_config",
                default="from_default",
            )
            assert result == "from_env"

    def test_config_third_priority(self) -> None:
        """Test that config has third priority."""
        args = argparse.Namespace(my_value=None)
        config = PykourConfig()

        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MY_ENV_VAR", None)
            result = get_config_value(
                key="test",
                args=args,
                args_attr="my_value",
                env_var="MY_ENV_VAR",
                config=config,
                config_getter=lambda c: "from_config",
                default="from_default",
            )
            assert result == "from_config"

    def test_default_lowest_priority(self) -> None:
        """Test that default has lowest priority."""
        args = argparse.Namespace(my_value=None)
        config = PykourConfig()

        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MY_ENV_VAR", None)
            result = get_config_value(
                key="test",
                args=args,
                args_attr="my_value",
                env_var="MY_ENV_VAR",
                config=config,
                config_getter=lambda c: None,
                default="from_default",
            )
            assert result == "from_default"

    def test_config_getter_exception_falls_through(self) -> None:
        """Test that exception in config_getter falls through to default."""
        args = argparse.Namespace(my_value=None)
        config = PykourConfig()

        def bad_getter(c: PykourConfig) -> str:
            raise AttributeError("no such attribute")

        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MY_ENV_VAR", None)
            result = get_config_value(
                key="test",
                args=args,
                args_attr="my_value",
                env_var="MY_ENV_VAR",
                config=config,
                config_getter=bad_getter,
                default="from_default",
            )
            assert result == "from_default"


class TestIntegrationWithToml:
    """Integration tests with TOML file loading."""

    def test_env_var_expansion_in_toml(self) -> None:
        """Test that environment variables in TOML are expanded."""
        toml_content = b"""
[database]
url = "${DATABASE_URL}"
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            try:
                with mock.patch.dict(
                    os.environ, {"DATABASE_URL": "sqlite:///expanded.db"}
                ):
                    os.environ.pop("PYKOUR_DATABASE_URL", None)
                    with mock.patch(
                        "pykour.config.loader.find_config_file",
                        return_value=Path(f.name),
                    ):
                        args = argparse.Namespace(database=None)
                        result = get_database_url_from_config(args)
                        assert result == "sqlite:///expanded.db"
            finally:
                os.unlink(f.name)

    def test_default_value_in_toml(self) -> None:
        """Test default value syntax in TOML."""
        toml_content = b"""
[database]
url = "${DATABASE_URL:-sqlite:///default.db}"
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            try:
                with mock.patch.dict(os.environ, {}, clear=True):
                    os.environ.pop("DATABASE_URL", None)
                    os.environ.pop("PYKOUR_DATABASE_URL", None)
                    with mock.patch(
                        "pykour.config.loader.find_config_file",
                        return_value=Path(f.name),
                    ):
                        args = argparse.Namespace(database=None)
                        result = get_database_url_from_config(args)
                        assert result == "sqlite:///default.db"
            finally:
                os.unlink(f.name)

    def test_pykour_database_url_overrides_toml(self) -> None:
        """Test that PYKOUR_DATABASE_URL overrides TOML value."""
        toml_content = b"""
[database]
url = "sqlite:///toml.db"
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(toml_content)
            f.flush()
            try:
                with mock.patch.dict(
                    os.environ, {"PYKOUR_DATABASE_URL": "sqlite:///env.db"}
                ):
                    with mock.patch(
                        "pykour.config.loader.find_config_file",
                        return_value=Path(f.name),
                    ):
                        args = argparse.Namespace(database=None)
                        result = get_database_url_from_config(args)
                        assert result == "sqlite:///env.db"
            finally:
                os.unlink(f.name)
