"""WHERE clause mixin for query builders."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self


class WhereClauseMixin:
    """Mixin providing comparison operator methods for queries with WHERE clauses."""

    _where_clauses: list[str]
    _add_param: Callable[[Any], str]
    _build_comparison: Callable[[str, str, Any], str]
    _build_in_clause: Callable[[str, list[Any], bool], str]
    _build_between: Callable[[str, Any, Any], str]

    def where_gt(self, column: str, value: Any) -> Self:
        """Add WHERE column > value condition.

        Args:
            column: Column name.
            value: Value to compare against.
        """
        self._where_clauses.append(self._build_comparison(column, ">", value))
        return self

    def where_gte(self, column: str, value: Any) -> Self:
        """Add WHERE column >= value condition.

        Args:
            column: Column name.
            value: Value to compare against.
        """
        self._where_clauses.append(self._build_comparison(column, ">=", value))
        return self

    def where_lt(self, column: str, value: Any) -> Self:
        """Add WHERE column < value condition.

        Args:
            column: Column name.
            value: Value to compare against.
        """
        self._where_clauses.append(self._build_comparison(column, "<", value))
        return self

    def where_lte(self, column: str, value: Any) -> Self:
        """Add WHERE column <= value condition.

        Args:
            column: Column name.
            value: Value to compare against.
        """
        self._where_clauses.append(self._build_comparison(column, "<=", value))
        return self

    def where_in(self, column: str, values: list[Any]) -> Self:
        """Add WHERE column IN (...) condition.

        Args:
            column: Column name.
            values: List of values.
        """
        self._where_clauses.append(self._build_in_clause(column, values, False))
        return self

    def where_not_in(self, column: str, values: list[Any]) -> Self:
        """Add WHERE column NOT IN (...) condition.

        Args:
            column: Column name.
            values: List of values.
        """
        self._where_clauses.append(self._build_in_clause(column, values, True))
        return self

    def where_between(self, column: str, min_val: Any, max_val: Any) -> Self:
        """Add WHERE column BETWEEN min AND max condition.

        Args:
            column: Column name.
            min_val: Minimum value (inclusive).
            max_val: Maximum value (inclusive).
        """
        self._where_clauses.append(self._build_between(column, min_val, max_val))
        return self

    def where_like(self, column: str, pattern: str) -> Self:
        """Add WHERE column LIKE pattern condition.

        Args:
            column: Column name.
            pattern: SQL LIKE pattern (use % for wildcards).
        """
        self._where_clauses.append(self._build_comparison(column, "LIKE", pattern))
        return self

    def where_is_null(self, column: str) -> Self:
        """Add WHERE column IS NULL condition.

        Args:
            column: Column name.
        """
        self._where_clauses.append(f"{column} IS NULL")
        return self

    def where_is_not_null(self, column: str) -> Self:
        """Add WHERE column IS NOT NULL condition.

        Args:
            column: Column name.
        """
        self._where_clauses.append(f"{column} IS NOT NULL")
        return self
