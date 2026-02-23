"""Tests for migration column types."""

from pykour.db.migrations.types import (
    BigInt,
    Binary,
    Boolean,
    Date,
    DateTime,
    Decimal,
    Float,
    Integer,
    JSON,
    SmallInt,
    String,
    Text,
    Time,
    UUID,
)


class TestInteger:
    """Tests for Integer type."""

    def test_to_sql_sqlite(self) -> None:
        """Integer should return INTEGER for SQLite."""
        assert Integer().to_sql("sqlite") == "INTEGER"

    def test_to_sql_postgresql(self) -> None:
        """Integer should return INTEGER for PostgreSQL."""
        assert Integer().to_sql("postgresql") == "INTEGER"

    def test_to_sql_mysql(self) -> None:
        """Integer should return INTEGER for MySQL."""
        assert Integer().to_sql("mysql") == "INTEGER"

    def test_big_integer(self) -> None:
        """Big integer should return BIGINT."""
        assert Integer(big=True).to_sql("sqlite") == "BIGINT"


class TestSmallInt:
    """Tests for SmallInt type."""

    def test_to_sql(self) -> None:
        """SmallInt should return SMALLINT."""
        assert SmallInt().to_sql("sqlite") == "SMALLINT"


class TestBigInt:
    """Tests for BigInt type."""

    def test_to_sql(self) -> None:
        """BigInt should return BIGINT."""
        assert BigInt().to_sql("sqlite") == "BIGINT"


class TestString:
    """Tests for String type."""

    def test_default_length(self) -> None:
        """String should default to 255 length."""
        assert String().to_sql("sqlite") == "VARCHAR(255)"

    def test_custom_length(self) -> None:
        """String should respect custom length."""
        assert String(100).to_sql("sqlite") == "VARCHAR(100)"


class TestText:
    """Tests for Text type."""

    def test_to_sql(self) -> None:
        """Text should return TEXT."""
        assert Text().to_sql("sqlite") == "TEXT"


class TestBoolean:
    """Tests for Boolean type."""

    def test_to_sql_sqlite(self) -> None:
        """Boolean should return INTEGER for SQLite."""
        assert Boolean().to_sql("sqlite") == "INTEGER"

    def test_to_sql_postgresql(self) -> None:
        """Boolean should return BOOLEAN for PostgreSQL."""
        assert Boolean().to_sql("postgresql") == "BOOLEAN"

    def test_to_sql_mysql(self) -> None:
        """Boolean should return TINYINT(1) for MySQL."""
        assert Boolean().to_sql("mysql") == "TINYINT(1)"


class TestFloat:
    """Tests for Float type."""

    def test_to_sql_sqlite(self) -> None:
        """Float should return FLOAT for SQLite."""
        assert Float().to_sql("sqlite") == "FLOAT"

    def test_to_sql_postgresql(self) -> None:
        """Float should return DOUBLE PRECISION for PostgreSQL."""
        assert Float().to_sql("postgresql") == "DOUBLE PRECISION"


class TestDecimal:
    """Tests for Decimal type."""

    def test_default_precision(self) -> None:
        """Decimal should default to (10, 2)."""
        assert Decimal().to_sql("sqlite") == "DECIMAL(10,2)"

    def test_custom_precision(self) -> None:
        """Decimal should respect custom precision."""
        assert Decimal(18, 4).to_sql("sqlite") == "DECIMAL(18,4)"


class TestDateTime:
    """Tests for DateTime type."""

    def test_to_sql_sqlite(self) -> None:
        """DateTime should return TIMESTAMP for SQLite."""
        assert DateTime().to_sql("sqlite") == "TIMESTAMP"

    def test_to_sql_postgresql(self) -> None:
        """DateTime should return TIMESTAMP for PostgreSQL by default."""
        assert DateTime().to_sql("postgresql") == "TIMESTAMP"

    def test_to_sql_postgresql_with_timezone(self) -> None:
        """DateTime(timezone=True) should return TIMESTAMPTZ for PostgreSQL."""
        assert DateTime(timezone=True).to_sql("postgresql") == "TIMESTAMPTZ"

    def test_to_sql_mysql(self) -> None:
        """DateTime should return DATETIME for MySQL."""
        assert DateTime().to_sql("mysql") == "DATETIME"


class TestDate:
    """Tests for Date type."""

    def test_to_sql(self) -> None:
        """Date should return DATE."""
        assert Date().to_sql("sqlite") == "DATE"


class TestTime:
    """Tests for Time type."""

    def test_to_sql(self) -> None:
        """Time should return TIME."""
        assert Time().to_sql("sqlite") == "TIME"


class TestBinary:
    """Tests for Binary type."""

    def test_to_sql_sqlite(self) -> None:
        """Binary should return BLOB for SQLite."""
        assert Binary().to_sql("sqlite") == "BLOB"

    def test_to_sql_postgresql(self) -> None:
        """Binary should return BYTEA for PostgreSQL."""
        assert Binary().to_sql("postgresql") == "BYTEA"

    def test_to_sql_mysql_no_length(self) -> None:
        """Binary should return BLOB for MySQL without length."""
        assert Binary().to_sql("mysql") == "BLOB"

    def test_to_sql_mysql_with_length(self) -> None:
        """Binary should return VARBINARY for MySQL with length."""
        assert Binary(255).to_sql("mysql") == "VARBINARY(255)"


class TestJSON:
    """Tests for JSON type."""

    def test_to_sql_sqlite(self) -> None:
        """JSON should return TEXT for SQLite."""
        assert JSON().to_sql("sqlite") == "TEXT"

    def test_to_sql_postgresql(self) -> None:
        """JSON should return JSONB for PostgreSQL."""
        assert JSON().to_sql("postgresql") == "JSONB"

    def test_to_sql_mysql(self) -> None:
        """JSON should return JSON for MySQL."""
        assert JSON().to_sql("mysql") == "JSON"


class TestUUID:
    """Tests for UUID type."""

    def test_to_sql_sqlite(self) -> None:
        """UUID should return VARCHAR(36) for SQLite."""
        assert UUID().to_sql("sqlite") == "VARCHAR(36)"

    def test_to_sql_postgresql(self) -> None:
        """UUID should return UUID for PostgreSQL."""
        assert UUID().to_sql("postgresql") == "UUID"
