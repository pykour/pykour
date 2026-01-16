"""SQL utility functions for identifier validation and quoting.

This module provides functions to validate and quote SQL identifiers
(table names, column names, etc.) to prevent SQL injection attacks.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Literal

# Valid SQL identifier pattern: starts with letter or underscore,
# followed by letters, digits, or underscores
_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Maximum identifier length (conservative limit across databases)
_MAX_IDENTIFIER_LENGTH = 128

# SQL reserved keywords that cannot be used as unquoted identifiers
_SQL_RESERVED_KEYWORDS = frozenset(
    {
        # ANSI SQL reserved words
        "add",
        "all",
        "alter",
        "and",
        "any",
        "as",
        "asc",
        "backup",
        "between",
        "by",
        "case",
        "check",
        "column",
        "constraint",
        "create",
        "database",
        "default",
        "delete",
        "desc",
        "distinct",
        "drop",
        "exec",
        "exists",
        "foreign",
        "from",
        "full",
        "group",
        "having",
        "in",
        "index",
        "inner",
        "insert",
        "into",
        "is",
        "join",
        "key",
        "left",
        "like",
        "limit",
        "not",
        "null",
        "on",
        "or",
        "order",
        "outer",
        "primary",
        "procedure",
        "right",
        "rownum",
        "select",
        "set",
        "table",
        "top",
        "truncate",
        "union",
        "unique",
        "update",
        "values",
        "view",
        "where",
        "with",
        # Additional commonly reserved words
        "abort",
        "action",
        "after",
        "analyze",
        "attach",
        "autoincrement",
        "before",
        "begin",
        "cascade",
        "cast",
        "collate",
        "commit",
        "conflict",
        "cross",
        "current",
        "current_date",
        "current_time",
        "current_timestamp",
        "deferrable",
        "deferred",
        "detach",
        "each",
        "else",
        "end",
        "escape",
        "except",
        "exclusive",
        "explain",
        "fail",
        "filter",
        "first",
        "following",
        "for",
        "glob",
        "if",
        "ignore",
        "immediate",
        "indexed",
        "initially",
        "instead",
        "intersect",
        "isnull",
        "last",
        "match",
        "natural",
        "no",
        "nothing",
        "notnull",
        "nulls",
        "of",
        "offset",
        "over",
        "partition",
        "plan",
        "pragma",
        "preceding",
        "query",
        "raise",
        "range",
        "recursive",
        "references",
        "regexp",
        "reindex",
        "release",
        "rename",
        "replace",
        "restrict",
        "returning",
        "rollback",
        "row",
        "rows",
        "savepoint",
        "temp",
        "temporary",
        "then",
        "ties",
        "to",
        "transaction",
        "trigger",
        "unbounded",
        "using",
        "vacuum",
        "virtual",
        "when",
        "window",
    }
)


class InvalidIdentifierError(ValueError):
    """Raised when an SQL identifier is invalid."""

    def __init__(
        self,
        identifier: str,
        identifier_type: str = "identifier",
        reason: str = "",
    ) -> None:
        self.identifier = identifier
        self.identifier_type = identifier_type
        self.reason = reason
        message = f"Invalid SQL {identifier_type}: {identifier!r}"
        if reason:
            message += f" ({reason})"
        super().__init__(message)


def validate_identifier(
    name: str,
    identifier_type: str = "identifier",
    *,
    allow_reserved: bool = False,
) -> str:
    """Validate an SQL identifier (table name, column name, etc.).

    Args:
        name: The identifier to validate.
        identifier_type: Type of identifier for error messages
            (e.g., "table", "column", "index").
        allow_reserved: If True, allow SQL reserved keywords as identifiers.

    Returns:
        The validated identifier (unchanged if valid).

    Raises:
        InvalidIdentifierError: If the identifier is invalid.

    Examples:
        >>> validate_identifier("users", "table")
        'users'
        >>> validate_identifier("user_id", "column")
        'user_id'
        >>> validate_identifier("123invalid", "table")
        Traceback (most recent call last):
            ...
        InvalidIdentifierError: Invalid SQL table: '123invalid' (...)
    """
    if not name:
        raise InvalidIdentifierError(
            name, identifier_type, "identifier cannot be empty"
        )

    if len(name) > _MAX_IDENTIFIER_LENGTH:
        raise InvalidIdentifierError(
            name,
            identifier_type,
            f"identifier exceeds maximum length of {_MAX_IDENTIFIER_LENGTH}",
        )

    if not _IDENTIFIER_PATTERN.match(name):
        raise InvalidIdentifierError(
            name,
            identifier_type,
            "must start with letter or underscore, "
            "followed by letters, digits, or underscores only",
        )

    if not allow_reserved and name.lower() in _SQL_RESERVED_KEYWORDS:
        raise InvalidIdentifierError(
            name,
            identifier_type,
            f"'{name}' is a SQL reserved keyword",
        )

    return name


def quote_identifier(
    name: str,
    driver_name: Literal["sqlite", "postgresql", "mysql"],
    *,
    validate: bool = True,
) -> str:
    """Quote an SQL identifier for the specified database driver.

    Args:
        name: The identifier to quote.
        driver_name: The database driver name.
        validate: If True, validate the identifier before quoting.

    Returns:
        The quoted identifier.

    Raises:
        InvalidIdentifierError: If validate is True and the identifier is invalid.

    Examples:
        >>> quote_identifier("users", "postgresql")
        '"users"'
        >>> quote_identifier("users", "mysql")
        '`users`'
        >>> quote_identifier("user name", "postgresql", validate=False)
        '"user name"'
    """
    if validate:
        validate_identifier(name, allow_reserved=True)

    if driver_name == "mysql":
        # MySQL uses backticks
        escaped = name.replace("`", "``")
        return f"`{escaped}`"
    else:
        # PostgreSQL and SQLite use double quotes
        escaped = name.replace('"', '""')
        return f'"{escaped}"'


def is_valid_identifier(name: str, *, allow_reserved: bool = False) -> bool:
    """Check if a string is a valid SQL identifier without raising.

    Args:
        name: The string to check.
        allow_reserved: If True, allow SQL reserved keywords.

    Returns:
        True if the string is a valid SQL identifier, False otherwise.

    Examples:
        >>> is_valid_identifier("users")
        True
        >>> is_valid_identifier("123invalid")
        False
        >>> is_valid_identifier("select")
        False
        >>> is_valid_identifier("select", allow_reserved=True)
        True
    """
    try:
        validate_identifier(name, allow_reserved=allow_reserved)
        return True
    except InvalidIdentifierError:
        return False


def validate_rls_condition(condition: str) -> str:
    """Validate a Row-Level Security (RLS) policy condition.

    This function validates RLS conditions to prevent SQL injection attacks.
    Only simple conditions with column references, operators, and parameters
    are allowed.

    Args:
        condition: The RLS condition to validate.

    Returns:
        The validated condition (unchanged if valid).

    Raises:
        InvalidIdentifierError: If the condition contains dangerous patterns.

    Examples:
        >>> validate_rls_condition("user_id = :current_user")
        'user_id = :current_user'
        >>> validate_rls_condition("tenant_id = :tenant")
        'tenant_id = :tenant'
    """
    if not condition:
        raise InvalidIdentifierError(
            condition, "RLS condition", "condition cannot be empty"
        )

    # Check for dangerous patterns
    dangerous_patterns = [
        (r";\s*", "semicolons are not allowed"),
        (r"--", "SQL comments are not allowed"),
        (r"/\*", "SQL comments are not allowed"),
        (r"\bunion\b", "UNION is not allowed"),
        (r"\bexec\b", "EXEC is not allowed"),
        (r"\bexecute\b", "EXECUTE is not allowed"),
        (r"\bdrop\b", "DROP is not allowed"),
        (r"\btruncate\b", "TRUNCATE is not allowed"),
        (r"\bdelete\b", "DELETE is not allowed"),
        (r"\binsert\b", "INSERT is not allowed"),
        (r"\bupdate\b", "UPDATE is not allowed"),
        (r"\bcreate\b", "CREATE is not allowed"),
        (r"\balter\b", "ALTER is not allowed"),
        (r"\bgrant\b", "GRANT is not allowed"),
        (r"\brevoke\b", "REVOKE is not allowed"),
    ]

    condition_lower = condition.lower()
    for pattern, reason in dangerous_patterns:
        if re.search(pattern, condition_lower, re.IGNORECASE):
            raise InvalidIdentifierError(condition, "RLS condition", reason)

    return condition
