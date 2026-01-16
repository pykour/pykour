"""Dependency injection for database.

.. deprecated::
    This module is deprecated. Use ``pykour.di.Depends`` instead.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pykour.db.database import Database


class Depends:
    """Dependency injection marker for database.

    .. deprecated::
        Use ``pykour.di.Depends`` instead. This class is maintained
        for backward compatibility and will be removed in a future release.

    Example (deprecated):
        from pykour.db import Database, Depends

        async def get(request: Request, db: Database = Depends()) -> JSONResponse:
            ...

    Migration:
        # Old (deprecated)
        from pykour.db import Database, Depends
        async def handler(db: Database = Depends()) -> JSONResponse: ...

        # New (recommended)
        from pykour.di import Depends
        from pykour.db import Database
        async def handler(db: Database = Depends()) -> JSONResponse: ...
    """

    def __init__(self, db: "Database | None" = None) -> None:
        """Initialize Depends marker.

        Args:
            db: Optional specific database instance. If None, uses the
                application's configured database.
        """
        warnings.warn(
            "pykour.db.Depends is deprecated. Use pykour.di.Depends instead. "
            "See migration guide in class docstring.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._db = db

    @property
    def database(self) -> "Database | None":
        """Get the specified database instance."""
        return self._db
