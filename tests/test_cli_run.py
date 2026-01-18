"""Tests for CLI run command."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

from pykour.cli.commands.run import cmd_run, register_command


class TestRunCommandArguments:
    """Test run command argument parsing."""

    def test_reload_dir_argument(self) -> None:
        """--reload-dir argument should be registered."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--reload-dir", "src"])
        assert args.reload_dirs == ["src"]

    def test_reload_dir_multiple(self) -> None:
        """--reload-dir can be specified multiple times."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["run", "app:app", "--reload-dir", "src", "--reload-dir", "lib"]
        )
        assert args.reload_dirs == ["src", "lib"]

    def test_reload_include_argument(self) -> None:
        """--reload-include argument should be registered."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--reload-include", "*.py"])
        assert args.reload_includes == ["*.py"]

    def test_reload_include_multiple(self) -> None:
        """--reload-include can be specified multiple times."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            [
                "run",
                "app:app",
                "--reload-include",
                "*.py",
                "--reload-include",
                "*.yaml",
            ]
        )
        assert args.reload_includes == ["*.py", "*.yaml"]

    def test_reload_exclude_argument(self) -> None:
        """--reload-exclude argument should be registered."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--reload-exclude", "*.pyc"])
        assert args.reload_excludes == ["*.pyc"]

    def test_reload_exclude_multiple(self) -> None:
        """--reload-exclude can be specified multiple times."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            [
                "run",
                "app:app",
                "--reload-exclude",
                "*.pyc",
                "--reload-exclude",
                "__pycache__",
            ]
        )
        assert args.reload_excludes == ["*.pyc", "__pycache__"]

    def test_debug_argument(self) -> None:
        """--debug argument should be registered."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--debug"])
        assert args.debug is True

    def test_debug_default_false(self) -> None:
        """--debug should default to False."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app"])
        assert args.debug is False

    def test_reload_dirs_default_none(self) -> None:
        """--reload-dir should default to None."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app"])
        assert args.reload_dirs is None

    def test_reload_includes_default_none(self) -> None:
        """--reload-include should default to None."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app"])
        assert args.reload_includes is None

    def test_reload_excludes_default_none(self) -> None:
        """--reload-exclude should default to None."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app"])
        assert args.reload_excludes is None


class TestRunCommandExecution:
    """Test run command execution."""

    @patch("uvicorn.run")
    def test_debug_enables_reload(self, mock_uvicorn_run: MagicMock) -> None:
        """--debug should auto-enable reload."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--debug"])
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["reload"] is True

    @patch("uvicorn.run")
    def test_debug_sets_log_level_debug(self, mock_uvicorn_run: MagicMock) -> None:
        """--debug should set log level to DEBUG."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--debug"])
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["log_level"] == "debug"

    @patch("uvicorn.run")
    def test_debug_sets_pykour_debug_env(self, mock_uvicorn_run: MagicMock) -> None:
        """--debug should set PYKOUR_DEBUG environment variable."""
        import os

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--debug"])

        # Clear the env var before test
        if "PYKOUR_DEBUG" in os.environ:
            del os.environ["PYKOUR_DEBUG"]

        cmd_run(args)

        assert os.environ.get("PYKOUR_DEBUG") == "1"

        # Cleanup
        del os.environ["PYKOUR_DEBUG"]

    @patch("uvicorn.run")
    def test_reload_dirs_passed_to_uvicorn(self, mock_uvicorn_run: MagicMock) -> None:
        """--reload-dir should be passed to uvicorn."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["run", "app:app", "--reload", "--reload-dir", "src", "--reload-dir", "lib"]
        )
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["reload_dirs"] == ["src", "lib"]

    @patch("uvicorn.run")
    def test_reload_includes_passed_to_uvicorn(
        self, mock_uvicorn_run: MagicMock
    ) -> None:
        """--reload-include should be passed to uvicorn."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            [
                "run",
                "app:app",
                "--reload",
                "--reload-include",
                "*.py",
                "--reload-include",
                "*.yaml",
            ]
        )
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["reload_includes"] == ["*.py", "*.yaml"]

    @patch("uvicorn.run")
    def test_reload_excludes_passed_to_uvicorn(
        self, mock_uvicorn_run: MagicMock
    ) -> None:
        """--reload-exclude should be passed to uvicorn."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            [
                "run",
                "app:app",
                "--reload",
                "--reload-exclude",
                "*.pyc",
                "--reload-exclude",
                "__pycache__",
            ]
        )
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["reload_excludes"] == ["*.pyc", "__pycache__"]

    @patch("uvicorn.run")
    def test_reload_options_none_when_not_specified(
        self, mock_uvicorn_run: MagicMock
    ) -> None:
        """Reload options should be None when not specified."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--reload"])
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["reload_dirs"] is None
        assert call_kwargs["reload_includes"] is None
        assert call_kwargs["reload_excludes"] is None

    @patch("uvicorn.run")
    def test_workers_set_to_1_when_debug(self, mock_uvicorn_run: MagicMock) -> None:
        """Workers should be set to 1 when --debug is specified."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--debug", "--workers", "4"])
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["workers"] == 1

    @patch("uvicorn.run")
    def test_default_app_name_when_not_specified(
        self, mock_uvicorn_run: MagicMock
    ) -> None:
        """Default app name should be 'app' when only module is specified."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "mymodule"])
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_args = mock_uvicorn_run.call_args
        assert call_args[1]["app"] == "mymodule:app"

    @patch("uvicorn.run")
    def test_custom_app_name(self, mock_uvicorn_run: MagicMock) -> None:
        """Custom app name should be used when specified."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "mymodule:application"])
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_args = mock_uvicorn_run.call_args
        assert call_args[1]["app"] == "mymodule:application"

    @patch("uvicorn.run")
    def test_custom_host_port(self, mock_uvicorn_run: MagicMock) -> None:
        """Custom host and port should be passed to uvicorn."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(
            ["run", "app:app", "--host", "0.0.0.0", "--port", "3000"]
        )
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["host"] == "0.0.0.0"
        assert call_kwargs["port"] == 3000

    @patch("uvicorn.run")
    def test_log_level_passed_to_uvicorn(self, mock_uvicorn_run: MagicMock) -> None:
        """Log level should be passed to uvicorn in lowercase."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--log-level", "WARNING"])
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["log_level"] == "warning"

    @patch("uvicorn.run")
    def test_workers_respected_without_reload(
        self, mock_uvicorn_run: MagicMock
    ) -> None:
        """Workers count should be respected when reload is not enabled."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app", "--workers", "4"])
        cmd_run(args)

        mock_uvicorn_run.assert_called_once()
        call_kwargs = mock_uvicorn_run.call_args[1]
        assert call_kwargs["workers"] == 4


class TestRunCommandErrorHandling:
    """Test run command error handling."""

    def test_missing_uvicorn_returns_error(self) -> None:
        """Should return error code 1 when uvicorn is not installed."""
        import builtins
        import sys

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app"])

        # Save original import function
        original_import = builtins.__import__

        def mock_import(
            name: str,
            globals: dict[str, object] | None = None,
            locals: dict[str, object] | None = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> object:
            if name == "uvicorn":
                raise ImportError("No module named 'uvicorn'")
            return original_import(name, globals, locals, fromlist, level)

        # Remove uvicorn from cached modules and mock import
        uvicorn_backup = sys.modules.pop("uvicorn", None)
        builtins.__import__ = mock_import  # type: ignore[assignment]

        try:
            result = cmd_run(args)
            assert result == 1
        finally:
            # Restore original import and module
            builtins.__import__ = original_import
            if uvicorn_backup is not None:
                sys.modules["uvicorn"] = uvicorn_backup

    @patch("uvicorn.run")
    def test_invalid_app_path_missing_module(self, mock_uvicorn_run: MagicMock) -> None:
        """Should return error code 1 for invalid app path with missing module."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", ":app"])
        result = cmd_run(args)

        assert result == 1
        mock_uvicorn_run.assert_not_called()

    @patch("uvicorn.run", side_effect=Exception("Server error"))
    def test_server_exception_returns_error(self, mock_uvicorn_run: MagicMock) -> None:
        """Should return error code 1 when uvicorn.run raises exception."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app"])
        result = cmd_run(args)

        assert result == 1

    @patch("uvicorn.run", side_effect=KeyboardInterrupt())
    def test_keyboard_interrupt_returns_success(
        self, mock_uvicorn_run: MagicMock
    ) -> None:
        """Should return exit code 0 when server is stopped with Ctrl+C."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["run", "app:app"])
        result = cmd_run(args)

        assert result == 0


class TestRunCommandValidation:
    """Test run command argument validation."""

    def test_positive_int_valid(self) -> None:
        """positive_int should accept valid positive integers."""
        from pykour.cli.commands.run import positive_int

        assert positive_int("1") == 1
        assert positive_int("10") == 10
        assert positive_int("100") == 100

    def test_positive_int_rejects_zero(self) -> None:
        """positive_int should reject zero."""
        from pykour.cli.commands.run import positive_int
        import pytest

        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 1"):
            positive_int("0")

    def test_positive_int_rejects_negative(self) -> None:
        """positive_int should reject negative integers."""
        from pykour.cli.commands.run import positive_int
        import pytest

        with pytest.raises(argparse.ArgumentTypeError, match="must be >= 1"):
            positive_int("-1")

    def test_positive_int_rejects_non_integer(self) -> None:
        """positive_int should reject non-integer values."""
        from pykour.cli.commands.run import positive_int
        import pytest

        with pytest.raises(argparse.ArgumentTypeError, match="invalid int value"):
            positive_int("abc")

        with pytest.raises(argparse.ArgumentTypeError, match="invalid int value"):
            positive_int("1.5")
