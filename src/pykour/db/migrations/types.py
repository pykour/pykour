"""Column type definitions for migrations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ColumnType(ABC):
    """Base class for column types."""

    @abstractmethod
    def to_sql(self, driver: str) -> str:
        """Convert to SQL type string for the given driver."""


class Integer(ColumnType):
    """Integer column type."""

    def __init__(self, big: bool = False) -> None:
        self.big = big

    def to_sql(self, driver: str) -> str:
        if self.big:
            if driver == "mysql":
                return "BIGINT"
            return "BIGINT"
        return "INTEGER"


class SmallInt(ColumnType):
    """Small integer column type."""

    def to_sql(self, driver: str) -> str:
        return "SMALLINT"


class BigInt(ColumnType):
    """Big integer column type."""

    def to_sql(self, driver: str) -> str:
        return "BIGINT"


class String(ColumnType):
    """Variable-length string column type."""

    def __init__(self, length: int = 255) -> None:
        self.length = length

    def to_sql(self, driver: str) -> str:
        return f"VARCHAR({self.length})"


class Text(ColumnType):
    """Text column type for long strings."""

    def to_sql(self, driver: str) -> str:
        return "TEXT"


class Boolean(ColumnType):
    """Boolean column type."""

    def to_sql(self, driver: str) -> str:
        if driver == "sqlite":
            return "INTEGER"
        if driver == "mysql":
            return "TINYINT(1)"
        return "BOOLEAN"


class Float(ColumnType):
    """Floating-point column type."""

    def to_sql(self, driver: str) -> str:
        if driver == "postgresql":
            return "DOUBLE PRECISION"
        return "FLOAT"


class Decimal(ColumnType):
    """Decimal column type with precision and scale."""

    def __init__(self, precision: int = 10, scale: int = 2) -> None:
        self.precision = precision
        self.scale = scale

    def to_sql(self, driver: str) -> str:
        return f"DECIMAL({self.precision},{self.scale})"


class DateTime(ColumnType):
    """DateTime column type."""

    def to_sql(self, driver: str) -> str:
        if driver == "postgresql":
            return "TIMESTAMP"
        if driver == "mysql":
            return "DATETIME"
        return "TIMESTAMP"


class Date(ColumnType):
    """Date column type."""

    def to_sql(self, driver: str) -> str:
        return "DATE"


class Time(ColumnType):
    """Time column type."""

    def to_sql(self, driver: str) -> str:
        return "TIME"


class Binary(ColumnType):
    """Binary/Blob column type."""

    def __init__(self, length: int | None = None) -> None:
        self.length = length

    def to_sql(self, driver: str) -> str:
        if driver == "postgresql":
            return "BYTEA"
        if driver == "mysql":
            if self.length:
                return f"VARBINARY({self.length})"
            return "BLOB"
        return "BLOB"


class JSON(ColumnType):
    """JSON column type."""

    def to_sql(self, driver: str) -> str:
        if driver == "sqlite":
            return "TEXT"
        if driver == "mysql":
            return "JSON"
        return "JSONB"


class UUID(ColumnType):
    """UUID column type."""

    def to_sql(self, driver: str) -> str:
        if driver == "postgresql":
            return "UUID"
        return "VARCHAR(36)"
