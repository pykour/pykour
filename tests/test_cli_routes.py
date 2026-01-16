"""Tests for CLI routes command."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

from pykour.cli.commands.routes import cmd_routes, register_command


class TestRoutesCommandArguments:
    """Test routes command argument parsing."""

    def test_routes_command_registered(self) -> None:
        """routes command should be registered."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes"])
        assert hasattr(args, "func")
        assert args.func == cmd_routes

    def test_routes_dir_argument(self) -> None:
        """--routes-dir argument should be registered."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes", "--routes-dir", "custom_routes"])
        assert args.routes_dir == "custom_routes"

    def test_routes_dir_default(self) -> None:
        """--routes-dir should default to 'routes'."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes"])
        assert args.routes_dir == "routes"

    def test_verbose_argument(self) -> None:
        """--verbose argument should be registered."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes", "--verbose"])
        assert args.verbose is True

    def test_verbose_short_argument(self) -> None:
        """-v argument should work as --verbose."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes", "-v"])
        assert args.verbose is True

    def test_verbose_default_false(self) -> None:
        """--verbose should default to False."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes"])
        assert args.verbose is False


class TestRoutesCommandExecution:
    """Test routes command execution."""

    def test_routes_nonexistent_dir(self, capsys: object) -> None:
        """Should return error for nonexistent directory."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes", "--routes-dir", "nonexistent_dir_xyz"])
        result = cmd_routes(args)

        assert result == 1
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "Error" in captured.out
        assert "not found" in captured.out

    def test_routes_empty_dir(self, tmp_path: Path, capsys: object) -> None:
        """Should show 'No routes found' for empty directory."""
        empty_routes_dir = tmp_path / "empty_routes"
        empty_routes_dir.mkdir()

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes", "--routes-dir", str(empty_routes_dir)])
        result = cmd_routes(args)

        assert result == 0
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "No routes found" in captured.out

    def test_routes_display(self, tmp_path: Path, capsys: object) -> None:
        """Should display routes correctly."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            'from pykour import JSONResponse\nasync def get(): return JSONResponse({"ok": True})'
        )

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes", "--routes-dir", str(routes_dir)])
        result = cmd_routes(args)

        assert result == 0
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "Registered routes" in captured.out
        assert "1 total" in captured.out
        assert "GET" in captured.out
        assert "/" in captured.out

    def test_routes_display_multiple_methods(
        self, tmp_path: Path, capsys: object
    ) -> None:
        """Should display multiple methods for a route."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            "from pykour import JSONResponse\n"
            'async def get(): return JSONResponse({"ok": True})\n'
            'async def post(): return JSONResponse({"ok": True})\n'
        )

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes", "--routes-dir", str(routes_dir)])
        result = cmd_routes(args)

        assert result == 0
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "GET" in captured.out
        assert "POST" in captured.out

    def test_routes_verbose_mode(self, tmp_path: Path, capsys: object) -> None:
        """Should display detailed info in verbose mode."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            'from pykour import JSONResponse\nasync def get(): return JSONResponse({"ok": True})'
        )

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes", "--routes-dir", str(routes_dir), "-v"])
        result = cmd_routes(args)

        assert result == 0
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "Methods:" in captured.out

    def test_routes_with_path_params(self, tmp_path: Path, capsys: object) -> None:
        """Should display path parameters in verbose mode."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        users_dir = routes_dir / "users" / "[id]"
        users_dir.mkdir(parents=True)
        (users_dir / "route.py").write_text(
            "from pykour import JSONResponse\n"
            'async def get(id: str): return JSONResponse({"id": id})'
        )

        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()
        register_command(subparsers)

        args = parser.parse_args(["routes", "--routes-dir", str(routes_dir), "-v"])
        result = cmd_routes(args)

        assert result == 0
        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert "Parameters:" in captured.out
        assert "id" in captured.out


class TestRoutesCommandIntegration:
    """Test routes command integration with main CLI."""

    def test_routes_from_main(self) -> None:
        """routes command should be accessible from main CLI."""
        from pykour.cli.main import main

        with patch("pykour.cli.commands.routes.cmd_routes", return_value=0) as mock_cmd:
            main(["routes", "--routes-dir", "test_routes"])
            mock_cmd.assert_called_once()
