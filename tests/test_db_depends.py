"""Tests for deprecated pykour.db.depends module."""

from __future__ import annotations

import warnings
from unittest.mock import MagicMock

import pytest


class TestDepends:
    """Tests for deprecated Depends class."""

    def test_deprecation_warning_raised(self) -> None:
        """Test that DeprecationWarning is raised on instantiation."""
        from pykour.db.depends import Depends

        with pytest.warns(DeprecationWarning) as warning_info:
            Depends()

        assert len(warning_info) == 1
        assert "pykour.db.Depends is deprecated" in str(warning_info[0].message)
        assert "pykour.di.Depends" in str(warning_info[0].message)

    def test_deprecation_warning_message_content(self) -> None:
        """Test that deprecation warning contains migration guide reference."""
        from pykour.db.depends import Depends

        with pytest.warns(DeprecationWarning) as warning_info:
            Depends()

        message = str(warning_info[0].message)
        assert "migration guide" in message.lower()

    def test_database_property_returns_none_when_not_specified(self) -> None:
        """Test that database property returns None when no db is specified."""
        from pykour.db.depends import Depends

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            depends = Depends()

        assert depends.database is None

    def test_database_property_returns_specified_database(self) -> None:
        """Test that database property returns the specified database instance."""
        from pykour.db.depends import Depends

        mock_db = MagicMock()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            depends = Depends(db=mock_db)

        assert depends.database is mock_db

    def test_database_stored_in_private_attribute(self) -> None:
        """Test that database is stored in _db private attribute."""
        from pykour.db.depends import Depends

        mock_db = MagicMock()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            depends = Depends(db=mock_db)

        assert depends._db is mock_db
