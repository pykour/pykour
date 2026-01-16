"""Tests for CLI interactive utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass


class MockMigration:
    """Mock migration object for testing."""

    def __init__(self, version: str, name: str) -> None:
        self.version = version
        self.name = name


class TestSelectMigrations:
    """Tests for select_migrations function."""

    def test_import_error_when_questionary_not_installed(self) -> None:
        """Test ImportError is raised when questionary is not installed."""
        from pykour.cli.interactive import select_migrations

        with patch.dict("sys.modules", {"questionary": None}):
            with pytest.raises(ImportError) as exc_info:
                select_migrations([], {}, set())
            assert "questionary is required" in str(exc_info.value)

    def test_returns_empty_list_when_user_cancels(self) -> None:
        """Test that empty list is returned when user cancels."""
        from pykour.cli.interactive import select_migrations

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.return_value = None

        mock_questionary = MagicMock()
        mock_questionary.checkbox = mock_checkbox
        mock_questionary.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = select_migrations([], {}, set())
            assert result == []

    def test_returns_selected_migrations(self) -> None:
        """Test that selected migrations are returned."""
        from pykour.cli.interactive import select_migrations

        m1 = MockMigration("20240101_000000", "create_users")
        m2 = MockMigration("20240102_000000", "add_email")

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.return_value = [m1, m2]

        mock_questionary = MagicMock()
        mock_questionary.checkbox = mock_checkbox
        mock_questionary.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

        groups = {"users": [m1, m2]}

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = select_migrations([m1, m2], groups, set())
            assert result == [m1, m2]

    def test_filters_none_values_from_selection(self) -> None:
        """Test that None values (group headers) are filtered out."""
        from pykour.cli.interactive import select_migrations

        m1 = MockMigration("20240101_000000", "create_users")

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.return_value = [None, m1, None]

        mock_questionary = MagicMock()
        mock_questionary.checkbox = mock_checkbox
        mock_questionary.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

        groups = {"users": [m1]}

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = select_migrations([m1], groups, set())
            assert result == [m1]
            assert None not in result

    def test_groups_sorted_with_special_groups_last(self) -> None:
        """Test that (no tables) and multiple tables groups are sorted last."""
        from pykour.cli.interactive import select_migrations

        m1 = MockMigration("20240101_000000", "create_users")
        m2 = MockMigration("20240102_000000", "add_posts")
        m3 = MockMigration("20240103_000000", "alter_both")
        m4 = MockMigration("20240104_000000", "add_index")

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.return_value = []

        mock_choice_calls: list[dict[str, Any]] = []

        def capture_choice(**kwargs: Any) -> dict[str, Any]:
            mock_choice_calls.append(kwargs)
            return kwargs

        mock_questionary = MagicMock()
        mock_questionary.checkbox = mock_checkbox
        mock_questionary.Choice = MagicMock(side_effect=capture_choice)

        groups = {
            "(no tables)": [m4],
            "users": [m1],
            "multiple tables": [m3],
            "posts": [m2],
        }

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            select_migrations([m1, m2, m3, m4], groups, set())

        # Extract group headers from choices
        headers = [c["title"] for c in mock_choice_calls if "─" in str(c.get("title", ""))]
        # posts and users should come before (no tables) and multiple tables
        assert len(headers) == 4
        # First two should be posts and users (alphabetical)
        assert "posts" in headers[0] or "users" in headers[0]

    def test_applied_status_shown(self) -> None:
        """Test that applied/pending status is shown correctly."""
        from pykour.cli.interactive import select_migrations

        m1 = MockMigration("20240101_000000", "create_users")
        m2 = MockMigration("20240102_000000", "add_email")

        mock_checkbox = MagicMock()
        mock_checkbox.return_value.ask.return_value = []

        mock_choice_calls: list[dict[str, Any]] = []

        def capture_choice(**kwargs: Any) -> dict[str, Any]:
            mock_choice_calls.append(kwargs)
            return kwargs

        mock_questionary = MagicMock()
        mock_questionary.checkbox = mock_checkbox
        mock_questionary.Choice = MagicMock(side_effect=capture_choice)

        groups = {"users": [m1, m2]}
        applied_versions = {"20240101_000000"}

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            select_migrations([m1, m2], groups, applied_versions)

        # Find migration choices (not headers)
        migration_choices = [
            c for c in mock_choice_calls
            if c.get("value") is not None and "─" not in str(c.get("title", ""))
        ]

        # Check that status is shown
        titles = [str(c.get("title", "")) for c in migration_choices]
        applied_count = sum(1 for t in titles if "(applied)" in t)
        pending_count = sum(1 for t in titles if "(pending)" in t)

        assert applied_count == 1
        assert pending_count == 1


class TestConfirmSquash:
    """Tests for confirm_squash function."""

    def test_with_questionary_returns_true_on_confirm(self) -> None:
        """Test that True is returned when user confirms."""
        from pykour.cli.interactive import confirm_squash

        m1 = MockMigration("20240101_000000", "create_users")

        mock_confirm = MagicMock()
        mock_confirm.return_value.ask.return_value = True

        mock_questionary = MagicMock()
        mock_questionary.confirm = mock_confirm

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = confirm_squash([m1], [])
            assert result is True

    def test_with_questionary_returns_false_on_decline(self) -> None:
        """Test that False is returned when user declines."""
        from pykour.cli.interactive import confirm_squash

        m1 = MockMigration("20240101_000000", "create_users")

        mock_confirm = MagicMock()
        mock_confirm.return_value.ask.return_value = False

        mock_questionary = MagicMock()
        mock_questionary.confirm = mock_confirm

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = confirm_squash([m1], [])
            assert result is False

    def test_with_questionary_handles_none_as_false(self) -> None:
        """Test that None (cancel) is treated as False."""
        from pykour.cli.interactive import confirm_squash

        m1 = MockMigration("20240101_000000", "create_users")

        mock_confirm = MagicMock()
        mock_confirm.return_value.ask.return_value = None

        mock_questionary = MagicMock()
        mock_questionary.confirm = mock_confirm

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = confirm_squash([m1], [])
            assert result is False

    def test_shows_pending_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that pending versions warning is shown."""
        from pykour.cli.interactive import confirm_squash

        m1 = MockMigration("20240101_000000", "create_users")

        mock_confirm = MagicMock()
        mock_confirm.return_value.ask.return_value = True

        mock_questionary = MagicMock()
        mock_questionary.confirm = mock_confirm

        pending = ["20240101_000000", "20240102_000000"]

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            confirm_squash([m1], pending)

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "20240101_000000" in captured.out
        assert "20240102_000000" in captured.out

    def test_fallback_to_simple_confirm_without_questionary(self) -> None:
        """Test fallback to simple confirm when questionary not available."""
        from pykour.cli.interactive import confirm_squash

        m1 = MockMigration("20240101_000000", "create_users")

        with patch.dict("sys.modules", {"questionary": None}):
            with patch("builtins.input", return_value="y"):
                result = confirm_squash([m1], [])
                assert result is True


class TestSimpleConfirm:
    """Tests for _simple_confirm function."""

    def test_returns_true_for_yes(self) -> None:
        """Test that True is returned for 'y' or 'yes'."""
        from pykour.cli.interactive import _simple_confirm

        m1 = MockMigration("20240101_000000", "create_users")

        with patch("builtins.input", return_value="y"):
            assert _simple_confirm([m1], []) is True

        with patch("builtins.input", return_value="yes"):
            assert _simple_confirm([m1], []) is True

        with patch("builtins.input", return_value="Y"):
            assert _simple_confirm([m1], []) is True

        with patch("builtins.input", return_value="YES"):
            assert _simple_confirm([m1], []) is True

    def test_returns_false_for_no(self) -> None:
        """Test that False is returned for 'n', 'no', or empty."""
        from pykour.cli.interactive import _simple_confirm

        m1 = MockMigration("20240101_000000", "create_users")

        with patch("builtins.input", return_value="n"):
            assert _simple_confirm([m1], []) is False

        with patch("builtins.input", return_value="no"):
            assert _simple_confirm([m1], []) is False

        with patch("builtins.input", return_value=""):
            assert _simple_confirm([m1], []) is False

        with patch("builtins.input", return_value="anything"):
            assert _simple_confirm([m1], []) is False

    def test_shows_pending_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that pending versions warning is shown."""
        from pykour.cli.interactive import _simple_confirm

        m1 = MockMigration("20240101_000000", "create_users")
        pending = ["20240101_000000"]

        with patch("builtins.input", return_value="n"):
            _simple_confirm([m1], pending)

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "20240101_000000" in captured.out


class TestSelectArchiveTarget:
    """Tests for select_archive_target function."""

    def test_returns_empty_when_no_available_migrations(self) -> None:
        """Test that empty list is returned when no migrations available."""
        from pykour.cli.interactive import select_archive_target

        result = select_archive_target([], None)
        assert result == []

    def test_returns_empty_when_all_archived(self) -> None:
        """Test that empty list is returned when all are already archived."""
        from pykour.cli.interactive import select_archive_target

        m1 = MockMigration("20240101_000000", "create_users")

        result = select_archive_target([m1], "20250101_000000")
        assert result == []

    def test_filters_by_current_boundary(self) -> None:
        """Test that migrations before boundary are excluded."""
        from pykour.cli.interactive import select_archive_target

        m1 = MockMigration("20240101_000000", "create_users")
        m2 = MockMigration("20240201_000000", "add_email")

        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "20240201_000000"

        mock_questionary = MagicMock()
        mock_questionary.select = mock_select
        mock_questionary.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

        # m1 should be excluded due to boundary
        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = select_archive_target([m1, m2], "20240101_000000")
            # Only m2 should be in the result (m2 is both available and <= selected)
            assert len(result) == 1
            assert result[0].version == "20240201_000000"

    def test_returns_empty_when_user_cancels(self) -> None:
        """Test that empty list is returned when user cancels."""
        from pykour.cli.interactive import select_archive_target

        m1 = MockMigration("20240101_000000", "create_users")

        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = None

        mock_questionary = MagicMock()
        mock_questionary.select = mock_select
        mock_questionary.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = select_archive_target([m1], None)
            assert result == []

    def test_returns_migrations_up_to_selected(self) -> None:
        """Test that all migrations up to selected version are returned."""
        from pykour.cli.interactive import select_archive_target

        m1 = MockMigration("20240101_000000", "create_users")
        m2 = MockMigration("20240102_000000", "add_email")
        m3 = MockMigration("20240103_000000", "add_posts")

        mock_select = MagicMock()
        mock_select.return_value.ask.return_value = "20240102_000000"

        mock_questionary = MagicMock()
        mock_questionary.select = mock_select
        mock_questionary.Choice = MagicMock(side_effect=lambda **kwargs: kwargs)

        with patch.dict("sys.modules", {"questionary": mock_questionary}):
            result = select_archive_target([m1, m2, m3], None)
            assert len(result) == 2
            versions = [m.version for m in result]
            assert "20240101_000000" in versions
            assert "20240102_000000" in versions
            assert "20240103_000000" not in versions

    def test_fallback_to_simple_select_without_questionary(self) -> None:
        """Test fallback to simple select when questionary not available."""
        from pykour.cli.interactive import select_archive_target

        m1 = MockMigration("20240101_000000", "create_users")

        with patch.dict("sys.modules", {"questionary": None}):
            with patch("builtins.input", return_value="1"):
                result = select_archive_target([m1], None)
                assert len(result) == 1
                assert result[0].version == "20240101_000000"


class TestSimpleSelectArchive:
    """Tests for _simple_select_archive function."""

    def test_returns_empty_on_quit(self) -> None:
        """Test that empty list is returned on quit."""
        from pykour.cli.interactive import _simple_select_archive

        m1 = MockMigration("20240101_000000", "create_users")

        with patch("builtins.input", return_value="q"):
            assert _simple_select_archive([m1], None) == []

        with patch("builtins.input", return_value="quit"):
            assert _simple_select_archive([m1], None) == []

        with patch("builtins.input", return_value=""):
            assert _simple_select_archive([m1], None) == []

    def test_returns_migrations_for_valid_selection(self) -> None:
        """Test that migrations are returned for valid selection."""
        from pykour.cli.interactive import _simple_select_archive

        m1 = MockMigration("20240101_000000", "create_users")
        m2 = MockMigration("20240102_000000", "add_email")

        with patch("builtins.input", return_value="2"):
            result = _simple_select_archive([m1, m2], None)
            assert len(result) == 2

        with patch("builtins.input", return_value="1"):
            result = _simple_select_archive([m1, m2], None)
            assert len(result) == 1
            assert result[0].version == "20240101_000000"

    def test_returns_empty_for_invalid_selection(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that empty list is returned for invalid selection."""
        from pykour.cli.interactive import _simple_select_archive

        m1 = MockMigration("20240101_000000", "create_users")

        with patch("builtins.input", return_value="invalid"):
            result = _simple_select_archive([m1], None)
            assert result == []

        captured = capsys.readouterr()
        assert "Invalid selection" in captured.out

    def test_returns_empty_for_out_of_range(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that empty list is returned for out of range selection."""
        from pykour.cli.interactive import _simple_select_archive

        m1 = MockMigration("20240101_000000", "create_users")

        with patch("builtins.input", return_value="99"):
            result = _simple_select_archive([m1], None)
            assert result == []

        captured = capsys.readouterr()
        assert "Invalid selection" in captured.out

    def test_shows_current_boundary(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that current boundary is shown."""
        from pykour.cli.interactive import _simple_select_archive

        m1 = MockMigration("20240101_000000", "create_users")

        with patch("builtins.input", return_value="q"):
            _simple_select_archive([m1], "20230101_000000")

        captured = capsys.readouterr()
        assert "Current archive boundary: 20230101_000000" in captured.out

    def test_lists_available_migrations(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that available migrations are listed."""
        from pykour.cli.interactive import _simple_select_archive

        m1 = MockMigration("20240101_000000", "create_users")
        m2 = MockMigration("20240102_000000", "add_email")

        with patch("builtins.input", return_value="q"):
            _simple_select_archive([m1, m2], None)

        captured = capsys.readouterr()
        assert "1. 20240101_000000_create_users" in captured.out
        assert "2. 20240102_000000_add_email" in captured.out
