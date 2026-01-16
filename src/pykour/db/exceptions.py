"""Database exceptions."""

import warnings


class DatabaseException(Exception):
    """Base exception for database errors."""


class DatabaseConnectionException(DatabaseException):
    """Exception raised when connecting to the database fails."""


class QueryException(DatabaseException):
    """Exception raised when executing a query fails."""


class TransactionException(DatabaseException):
    """Exception raised when transaction management fails."""


class DriverNotFoundException(DatabaseException):
    """Exception raised when a database driver is not found for the given URL scheme."""

    def __init__(self, scheme: str) -> None:
        super().__init__(f"No driver found for scheme: {scheme}")
        self.scheme = scheme


# Backward compatibility aliases
DatabaseError = DatabaseException
DatabaseConnectionError = DatabaseConnectionException
QueryError = QueryException
TransactionError = TransactionException
DriverNotFoundError = DriverNotFoundException


def __getattr__(name: str) -> type:
    """Provide deprecated alias for backward compatibility."""
    _deprecated_aliases = {
        "DBConnectionError": DatabaseConnectionException,
    }
    if name in _deprecated_aliases:
        warnings.warn(
            f"{name} is deprecated, use {_deprecated_aliases[name].__name__} instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return _deprecated_aliases[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
