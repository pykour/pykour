"""Tests for debug mode functionality."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from pykour import Pykour
from tests.helpers import MockSend, create_receive, create_scope


class TestDebugModeApplication:
    """Test Pykour debug mode functionality."""

    def test_debug_default_false(self, tmp_path: Path) -> None:
        """Debug mode should be disabled by default."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            'from pykour import JSONResponse\nasync def get(): return JSONResponse({"ok": True})'
        )

        # Clear any existing PYKOUR_DEBUG env var
        with patch.dict(os.environ, {}, clear=True):
            app = Pykour(routes_dir=str(routes_dir))
            assert app.debug is False

    def test_debug_explicit_true(self, tmp_path: Path) -> None:
        """Debug mode can be explicitly enabled."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            'from pykour import JSONResponse\nasync def get(): return JSONResponse({"ok": True})'
        )

        app = Pykour(routes_dir=str(routes_dir), debug=True)
        assert app.debug is True

    def test_debug_explicit_false(self, tmp_path: Path) -> None:
        """Debug mode can be explicitly disabled."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            'from pykour import JSONResponse\nasync def get(): return JSONResponse({"ok": True})'
        )

        app = Pykour(routes_dir=str(routes_dir), debug=False)
        assert app.debug is False

    def test_debug_from_environment_1(self, tmp_path: Path) -> None:
        """Debug mode can be set via PYKOUR_DEBUG=1 environment variable."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            'from pykour import JSONResponse\nasync def get(): return JSONResponse({"ok": True})'
        )

        with patch.dict(os.environ, {"PYKOUR_DEBUG": "1"}):
            app = Pykour(routes_dir=str(routes_dir))
            assert app.debug is True

    def test_debug_from_environment_true(self, tmp_path: Path) -> None:
        """Debug mode can be set via PYKOUR_DEBUG=true environment variable."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            'from pykour import JSONResponse\nasync def get(): return JSONResponse({"ok": True})'
        )

        with patch.dict(os.environ, {"PYKOUR_DEBUG": "true"}):
            app = Pykour(routes_dir=str(routes_dir))
            assert app.debug is True

    def test_debug_from_environment_yes(self, tmp_path: Path) -> None:
        """Debug mode can be set via PYKOUR_DEBUG=yes environment variable."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            'from pykour import JSONResponse\nasync def get(): return JSONResponse({"ok": True})'
        )

        with patch.dict(os.environ, {"PYKOUR_DEBUG": "yes"}):
            app = Pykour(routes_dir=str(routes_dir))
            assert app.debug is True

    def test_debug_explicit_overrides_env(self, tmp_path: Path) -> None:
        """Explicit debug parameter should override environment variable."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            'from pykour import JSONResponse\nasync def get(): return JSONResponse({"ok": True})'
        )

        with patch.dict(os.environ, {"PYKOUR_DEBUG": "1"}):
            app = Pykour(routes_dir=str(routes_dir), debug=False)
            assert app.debug is False


class TestDebugModeErrorHandling:
    """Test error handling in debug mode."""

    @pytest.mark.asyncio
    async def test_error_traceback_in_debug_mode(self, tmp_path: Path) -> None:
        """Debug mode should show traceback in error responses."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text("""
from pykour import JSONResponse

async def get():
    raise ValueError("Test error message")
""")

        app = Pykour(routes_dir=str(routes_dir), debug=True)

        scope = create_scope(method="GET", path="/")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 500
        data = send.json_body
        assert data["error"] == "Internal Server Error"
        assert data["detail"] == "Test error message"
        assert data["type"] == "ValueError"
        assert "traceback" in data
        assert isinstance(data["traceback"], list)
        # Traceback should contain the error message
        traceback_str = "".join(data["traceback"])
        assert "ValueError" in traceback_str
        assert "Test error message" in traceback_str

    @pytest.mark.asyncio
    async def test_error_generic_in_production_mode(self, tmp_path: Path) -> None:
        """Production mode should show generic error message."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text("""
from pykour import JSONResponse

async def get():
    raise ValueError("Test error message")
""")

        app = Pykour(routes_dir=str(routes_dir), debug=False)

        scope = create_scope(method="GET", path="/")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 500
        data = send.json_body
        assert data == {"error": "Internal Server Error"}
        assert "traceback" not in data
        assert "detail" not in data
        assert "type" not in data

    @pytest.mark.asyncio
    async def test_validation_error_not_affected_by_debug(self, tmp_path: Path) -> None:
        """ValidationError should return 422 regardless of debug mode."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text("""
from pykour import JSONResponse, Query

async def get(name: str = Query()):
    return JSONResponse({"name": name})
""")

        app = Pykour(routes_dir=str(routes_dir), debug=True)

        # Missing required query parameter
        scope = create_scope(method="GET", path="/")
        receive = create_receive()
        send = MockSend()

        await app(scope, receive, send)

        assert send.status == 422
        data = send.json_body
        assert "detail" in data
        # Should not have traceback (ValidationError is handled differently)
        assert "traceback" not in data or data.get("traceback") is None
