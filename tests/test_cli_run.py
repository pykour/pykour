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
