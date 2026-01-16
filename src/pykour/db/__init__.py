"""Database access module for Pykour."""

from pykour.db.database import Database
from pykour.db.exceptions import (
    # New exception names (preferred)
    DatabaseConnectionException,
    DatabaseException,
    DriverNotFoundException,
    QueryException,
    TransactionException,
    # Legacy aliases (backward compatibility)
    DatabaseConnectionError,
    DatabaseError,
    DriverNotFoundError,
    QueryError,
    TransactionError,
)
from pykour.db.query import DeleteQuery, InsertQuery, SelectQuery, UpdateQuery
from pykour.db.result import Row
from pykour.db.transaction import Transaction

__all__ = [
    # Main classes
    "Database",
    "Transaction",
    # Query builders
    "SelectQuery",
    "InsertQuery",
    "UpdateQuery",
    "DeleteQuery",
    # Result
    "Row",
    # Exceptions (new names)
    "DatabaseException",
    "DatabaseConnectionException",
    "QueryException",
    "TransactionException",
    "DriverNotFoundException",
    # Exceptions (legacy aliases)
    "DatabaseError",
    "DatabaseConnectionError",
    "QueryError",
    "TransactionError",
    "DriverNotFoundError",
]
