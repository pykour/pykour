"""Tests for database migrations system.

This module consolidates tests for:
- Column types (Integer, String, Boolean, etc.)
- Migration operations (CreateTable, DropTable, etc.)
- Table, Column, and Index definitions
"""

import pytest

from pykour.db.migrations.operations import (
    AddColumn,
    CreateIndex,
    CreateTable,
    DropColumn,
    DropIndex,
    DropTable,
    ExecuteSQL,
    RenameColumn,
    RenameTable,
)
from pykour.db.migrations.table import Column, ColumnDef, Index, Table
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


# =============================================================================
# Column Types Tests
# =============================================================================


class TestIntegerType:
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


class TestSmallIntType:
    """Tests for SmallInt type."""

    def test_to_sql(self) -> None:
        """SmallInt should return SMALLINT."""
        assert SmallInt().to_sql("sqlite") == "SMALLINT"


class TestBigIntType:
    """Tests for BigInt type."""

    def test_to_sql(self) -> None:
        """BigInt should return BIGINT."""
        assert BigInt().to_sql("sqlite") == "BIGINT"


class TestStringType:
    """Tests for String type."""

    def test_default_length(self) -> None:
        """String should default to 255 length."""
        assert String().to_sql("sqlite") == "VARCHAR(255)"

    def test_custom_length(self) -> None:
        """String should respect custom length."""
        assert String(100).to_sql("sqlite") == "VARCHAR(100)"


class TestTextType:
    """Tests for Text type."""

    def test_to_sql(self) -> None:
        """Text should return TEXT."""
        assert Text().to_sql("sqlite") == "TEXT"


class TestBooleanType:
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


class TestFloatType:
    """Tests for Float type."""

    def test_to_sql_sqlite(self) -> None:
        """Float should return FLOAT for SQLite."""
        assert Float().to_sql("sqlite") == "FLOAT"

    def test_to_sql_postgresql(self) -> None:
        """Float should return DOUBLE PRECISION for PostgreSQL."""
        assert Float().to_sql("postgresql") == "DOUBLE PRECISION"


class TestDecimalType:
    """Tests for Decimal type."""

    def test_default_precision(self) -> None:
        """Decimal should default to (10, 2)."""
        assert Decimal().to_sql("sqlite") == "DECIMAL(10,2)"

    def test_custom_precision(self) -> None:
        """Decimal should respect custom precision."""
        assert Decimal(18, 4).to_sql("sqlite") == "DECIMAL(18,4)"


class TestDateTimeType:
    """Tests for DateTime type."""

    def test_to_sql_sqlite(self) -> None:
        """DateTime should return TIMESTAMP for SQLite."""
        assert DateTime().to_sql("sqlite") == "TIMESTAMP"

    def test_to_sql_postgresql(self) -> None:
        """DateTime should return TIMESTAMP for PostgreSQL."""
        assert DateTime().to_sql("postgresql") == "TIMESTAMP"

    def test_to_sql_mysql(self) -> None:
        """DateTime should return DATETIME for MySQL."""
        assert DateTime().to_sql("mysql") == "DATETIME"


class TestDateType:
    """Tests for Date type."""

    def test_to_sql(self) -> None:
        """Date should return DATE."""
        assert Date().to_sql("sqlite") == "DATE"


class TestTimeType:
    """Tests for Time type."""

    def test_to_sql(self) -> None:
        """Time should return TIME."""
        assert Time().to_sql("sqlite") == "TIME"


class TestBinaryType:
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


class TestJSONType:
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


class TestUUIDType:
    """Tests for UUID type."""

    def test_to_sql_sqlite(self) -> None:
        """UUID should return VARCHAR(36) for SQLite."""
        assert UUID().to_sql("sqlite") == "VARCHAR(36)"

    def test_to_sql_postgresql(self) -> None:
        """UUID should return UUID for PostgreSQL."""
        assert UUID().to_sql("postgresql") == "UUID"


# =============================================================================
# Migration Operations Tests
# =============================================================================


class TestCreateTableOp:
    """Tests for CreateTable operation."""

    def test_to_code(self) -> None:
        """CreateTable should generate correct Python code."""
        columns = [
            ColumnDef("id", "INTEGER", primary_key=True, autoincrement=True),
            ColumnDef("name", "VARCHAR(100)", nullable=False),
        ]
        op = CreateTable("users", columns)
        code = op.to_code()

        assert "op.create_table(" in code
        assert '"users"' in code
        assert (
            'op.column("id", "INTEGER", primary_key=True, autoincrement=True)' in code
        )
        assert 'op.column("name", "VARCHAR(100)", nullable=False)' in code

    def test_reverse(self) -> None:
        """CreateTable reverse should be DropTable."""
        columns = [ColumnDef("id", "INTEGER", primary_key=True)]
        op = CreateTable("users", columns)
        reverse = op.reverse()

        assert isinstance(reverse, DropTable)
        assert reverse.name == "users"


class TestDropTableOp:
    """Tests for DropTable operation."""

    def test_to_code(self) -> None:
        """DropTable should generate correct Python code."""
        op = DropTable("users")
        code = op.to_code()

        assert 'op.drop_table("users")' == code


class TestAddColumnOp:
    """Tests for AddColumn operation."""

    def test_to_code(self) -> None:
        """AddColumn should generate correct Python code."""
        col = ColumnDef("email", "VARCHAR(255)", nullable=False, unique=True)
        op = AddColumn("users", col)
        code = op.to_code()

        assert 'op.add_column("users"' in code
        assert '"email"' in code
        assert '"VARCHAR(255)"' in code
        assert "nullable=False" in code
        assert "unique=True" in code

    def test_reverse(self) -> None:
        """AddColumn reverse should be DropColumn."""
        col = ColumnDef("email", "VARCHAR(255)")
        op = AddColumn("users", col)
        reverse = op.reverse()

        assert isinstance(reverse, DropColumn)
        assert reverse.table == "users"
        assert reverse.column_name == "email"


class TestDropColumnOp:
    """Tests for DropColumn operation."""

    def test_to_code(self) -> None:
        """DropColumn should generate correct Python code."""
        op = DropColumn("users", "email")
        code = op.to_code()

        assert 'op.drop_column("users", "email")' == code


class TestRenameTableOp:
    """Tests for RenameTable operation."""

    def test_to_code(self) -> None:
        """RenameTable should generate correct Python code."""
        op = RenameTable("users", "accounts")
        code = op.to_code()

        assert 'op.rename_table("users", "accounts")' == code

    def test_reverse(self) -> None:
        """RenameTable reverse should swap names."""
        op = RenameTable("users", "accounts")
        reverse = op.reverse()

        assert isinstance(reverse, RenameTable)
        assert reverse.old_name == "accounts"
        assert reverse.new_name == "users"


class TestRenameColumnOp:
    """Tests for RenameColumn operation."""

    def test_to_code(self) -> None:
        """RenameColumn should generate correct Python code."""
        op = RenameColumn("users", "name", "full_name")
        code = op.to_code()

        assert 'op.rename_column("users", "name", "full_name")' == code

    def test_reverse(self) -> None:
        """RenameColumn reverse should swap names."""
        op = RenameColumn("users", "name", "full_name")
        reverse = op.reverse()

        assert isinstance(reverse, RenameColumn)
        assert reverse.old_name == "full_name"
        assert reverse.new_name == "name"


class TestCreateIndexOp:
    """Tests for CreateIndex operation."""

    def test_to_code(self) -> None:
        """CreateIndex should generate correct Python code."""
        op = CreateIndex("idx_users_email", "users", ["email"])
        code = op.to_code()

        assert 'op.create_index("idx_users_email", "users", ["email"])' == code

    def test_to_code_unique(self) -> None:
        """CreateIndex should include unique flag."""
        op = CreateIndex("idx_users_email", "users", ["email"], unique=True)
        code = op.to_code()

        assert "unique=True" in code

    def test_reverse(self) -> None:
        """CreateIndex reverse should be DropIndex."""
        op = CreateIndex("idx_users_email", "users", ["email"])
        reverse = op.reverse()

        assert isinstance(reverse, DropIndex)
        assert reverse.name == "idx_users_email"

    def test_to_code_with_where(self) -> None:
        """CreateIndex should include WHERE clause."""
        op = CreateIndex("idx_active", "users", ["email"], where="active = 1")
        code = op.to_code()

        assert 'where="active = 1"' in code

    def test_to_code_unique_with_where(self) -> None:
        """CreateIndex should include both unique and WHERE clause."""
        op = CreateIndex(
            "idx_active", "users", ["email"], unique=True, where="active = 1"
        )
        code = op.to_code()

        assert "unique=True" in code
        assert 'where="active = 1"' in code

    def test_reverse_with_where(self) -> None:
        """CreateIndex with WHERE reverse should preserve WHERE clause."""
        op = CreateIndex("idx_active", "users", ["email"], where="active = 1")
        reverse = op.reverse()

        assert isinstance(reverse, DropIndex)
        assert reverse._index is not None
        assert reverse._index.where == "active = 1"


class TestDropIndexOp:
    """Tests for DropIndex operation."""

    def test_to_code(self) -> None:
        """DropIndex should generate correct Python code."""
        op = DropIndex("idx_users_email")
        code = op.to_code()

        assert 'op.drop_index("idx_users_email")' == code


class TestExecuteSQLOp:
    """Tests for ExecuteSQL operation."""

    def test_to_code(self) -> None:
        """ExecuteSQL should generate correct Python code."""
        op = ExecuteSQL(
            "CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1"
        )
        code = op.to_code()

        assert "op.execute(" in code
        assert "CREATE VIEW" in code

    def test_to_code_with_reverse(self) -> None:
        """ExecuteSQL with reverse should include reverse_sql."""
        op = ExecuteSQL(
            "CREATE VIEW active_users AS SELECT * FROM users WHERE active = 1",
            reverse_sql="DROP VIEW active_users",
        )
        code = op.to_code()

        assert "reverse_sql=" in code
        assert "DROP VIEW" in code

    def test_reverse(self) -> None:
        """ExecuteSQL reverse should swap SQL."""
        op = ExecuteSQL("CREATE VIEW v", reverse_sql="DROP VIEW v")
        reverse = op.reverse()

        assert isinstance(reverse, ExecuteSQL)
        assert reverse.sql == "DROP VIEW v"
        assert reverse.reverse_sql == "CREATE VIEW v"

    def test_reverse_without_reverse_sql(self) -> None:
        """ExecuteSQL without reverse_sql should raise."""
        op = ExecuteSQL("SELECT 1")

        with pytest.raises(ValueError):
            op.reverse()


# =============================================================================
# Table and Column Definition Tests
# =============================================================================


class TestColumn:
    """Tests for Column class."""

    def test_basic_column(self) -> None:
        """Basic column should have correct defaults."""
        col = Column(Integer())
        assert col.primary_key is False
        assert col.nullable is True
        assert col.unique is False
        assert col.default is None
        assert col.autoincrement is False

    def test_primary_key_column(self) -> None:
        """Primary key column should have correct settings."""
        col = Column(Integer(), primary_key=True, autoincrement=True)
        assert col.primary_key is True
        assert col.autoincrement is True

    def test_column_with_default(self) -> None:
        """Column with default should store it."""
        col = Column(Boolean(), default=True)
        assert col.default is True

    def test_column_to_sql_basic(self) -> None:
        """Column should generate correct SQL."""
        col = Column(String(100), nullable=False)
        col.name = "email"
        sql = col.to_sql("sqlite")
        assert "email" in sql
        assert "VARCHAR(100)" in sql
        assert "NOT NULL" in sql

    def test_column_to_sql_primary_key(self) -> None:
        """Primary key column should generate correct SQL."""
        col = Column(Integer(), primary_key=True, autoincrement=True)
        col.name = "id"
        sql = col.to_sql("sqlite")
        assert "id" in sql
        assert "INTEGER" in sql
        assert "PRIMARY KEY" in sql
        assert "AUTOINCREMENT" in sql

    def test_column_to_sql_with_default_bool(self) -> None:
        """Boolean default should be converted to integer."""
        col = Column(Boolean(), default=True)
        col.name = "active"
        sql = col.to_sql("sqlite")
        assert "DEFAULT 1" in sql

    def test_column_to_sql_with_default_string(self) -> None:
        """String default should be quoted."""
        col = Column(String(50), default="guest")
        col.name = "role"
        sql = col.to_sql("sqlite")
        assert "DEFAULT 'guest'" in sql

    def test_column_to_sql_with_default_timestamp(self) -> None:
        """now() default should use CURRENT_TIMESTAMP."""
        col = Column(DateTime(), default="now()")
        col.name = "created_at"
        sql = col.to_sql("sqlite")
        assert "DEFAULT CURRENT_TIMESTAMP" in sql


class TestColumnDef:
    """Tests for ColumnDef class."""

    def test_basic_column_def(self) -> None:
        """Basic ColumnDef should have correct defaults."""
        col = ColumnDef("id", "INTEGER")
        assert col.name == "id"
        assert col.type_sql == "INTEGER"
        assert col.primary_key is False
        assert col.nullable is True

    def test_column_def_to_sql(self) -> None:
        """ColumnDef should generate correct SQL."""
        col = ColumnDef(
            "email",
            "VARCHAR(255)",
            nullable=False,
            unique=True,
        )
        sql = col.to_sql("sqlite")
        assert "email" in sql
        assert "VARCHAR(255)" in sql
        assert "NOT NULL" in sql
        assert "UNIQUE" in sql


class TestTable:
    """Tests for Table class."""

    def test_table_definition(self) -> None:
        """Table should collect columns via metaclass."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True, autoincrement=True)
            name = Column(String(100), nullable=False)
            email = Column(String(255), unique=True, nullable=False)
            active = Column(Boolean(), default=True)

        columns = UserTable.get_columns()
        assert "id" in columns
        assert "name" in columns
        assert "email" in columns
        assert "active" in columns
        assert len(columns) == 4

    def test_table_get_tablename(self) -> None:
        """Table should return correct table name."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)

        assert UserTable.get_tablename() == "users"

    def test_table_get_column(self) -> None:
        """Table should return column by name."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)
            name = Column(String(100))

        col = UserTable.get_column("name")
        assert col is not None
        assert col.name == "name"

    def test_table_get_column_not_found(self) -> None:
        """Table should return None for unknown column."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)

        assert UserTable.get_column("unknown") is None

    def test_column_names_set(self) -> None:
        """Column names should be set by metaclass."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)
            name = Column(String(100))

        id_col = UserTable.get_column("id")
        name_col = UserTable.get_column("name")
        assert id_col is not None
        assert name_col is not None
        assert id_col.name == "id"
        assert name_col.name == "name"


class TestIndex:
    """Tests for Index class."""

    def test_basic_index(self) -> None:
        """Basic index should have correct defaults."""
        idx = Index(["email"])
        assert idx.columns == ["email"]
        assert idx.unique is False
        assert idx.where is None
        assert idx.name == ""

    def test_unique_index(self) -> None:
        """Unique index should have correct settings."""
        idx = Index(["email"], unique=True)
        assert idx.unique is True

    def test_partial_index(self) -> None:
        """Partial index should store WHERE clause."""
        idx = Index(["email"], where="active = 1")
        assert idx.where == "active = 1"

    def test_composite_index(self) -> None:
        """Composite index should store multiple columns."""
        idx = Index(["name", "created_at"])
        assert idx.columns == ["name", "created_at"]


class TestTableWithIndexes:
    """Tests for Table class with indexes."""

    def test_table_with_indexes(self) -> None:
        """Table should collect indexes via metaclass."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)
            email = Column(String(255))
            active = Column(Boolean(), default=True)

            idx_email = Index(["email"], unique=True)
            idx_active = Index(["email"], where="active = 1")

        indexes = UserTable.get_indexes()
        assert "idx_email" in indexes
        assert "idx_active" in indexes
        assert len(indexes) == 2

    def test_index_names_set(self) -> None:
        """Index names should be set by metaclass."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)
            email = Column(String(255))

            idx_email = Index(["email"])

        idx = UserTable.get_index("idx_email")
        assert idx is not None
        assert idx.name == "idx_email"

    def test_get_index_not_found(self) -> None:
        """Table should return None for unknown index."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)

        assert UserTable.get_index("unknown") is None

    def test_table_without_indexes(self) -> None:
        """Table without indexes should have empty indexes dict."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)

        indexes = UserTable.get_indexes()
        assert len(indexes) == 0


# =============================================================================
# Version Manager Tests
# =============================================================================

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from pykour.db.migrations.version import (
    MIGRATIONS_TABLE,
    MigrationRecord,
    VersionManager,
)


class TestMigrationRecord:
    """Tests for MigrationRecord dataclass."""

    def test_create_migration_record(self) -> None:
        """Test creating a MigrationRecord."""
        now = datetime.now()
        record = MigrationRecord(
            version="20240101_000000",
            name="create_users",
            applied_at=now,
        )
        assert record.version == "20240101_000000"
        assert record.name == "create_users"
        assert record.applied_at == now


class TestVersionManager:
    """Tests for VersionManager class."""

    def create_mock_driver(self, driver_name: str = "sqlite") -> MagicMock:
        """Create a mock driver for testing."""
        driver = MagicMock()
        driver.driver_name = driver_name
        driver.commit = AsyncMock()
        driver.execute = AsyncMock()
        driver.fetch_all = AsyncMock(return_value=[])
        driver.fetch_one = AsyncMock(return_value=None)
        return driver

    @pytest.mark.asyncio
    async def test_init_sqlite(self) -> None:
        """Test init creates SQLite migrations table."""
        driver = self.create_mock_driver("sqlite")
        manager = VersionManager(driver)
        conn = MagicMock()
        conn.execute = AsyncMock()

        await manager.init(conn)

        conn.execute.assert_called_once()
        sql = conn.execute.call_args[0][0]
        assert MIGRATIONS_TABLE in sql
        assert "TEXT PRIMARY KEY" in sql
        driver.commit.assert_called_once_with(conn)

    @pytest.mark.asyncio
    async def test_init_postgresql(self) -> None:
        """Test init creates PostgreSQL migrations table."""
        driver = self.create_mock_driver("postgresql")
        manager = VersionManager(driver)
        conn = MagicMock()
        conn.execute = AsyncMock()

        await manager.init(conn)

        sql = conn.execute.call_args[0][0]
        assert "VARCHAR(64) PRIMARY KEY" in sql

    @pytest.mark.asyncio
    async def test_init_mysql(self) -> None:
        """Test init creates MySQL migrations table."""
        driver = self.create_mock_driver("mysql")
        manager = VersionManager(driver)
        conn = MagicMock()
        conn.execute = AsyncMock()

        await manager.init(conn)

        sql = conn.execute.call_args[0][0]
        assert "VARCHAR(64) PRIMARY KEY" in sql

    @pytest.mark.asyncio
    async def test_get_applied_returns_empty_list(self) -> None:
        """Test get_applied returns empty list when no migrations."""
        driver = self.create_mock_driver()
        driver.fetch_all = AsyncMock(return_value=[])
        manager = VersionManager(driver)
        conn = MagicMock()

        result = await manager.get_applied(conn)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_applied_returns_migration_records(self) -> None:
        """Test get_applied returns MigrationRecord objects."""
        driver = self.create_mock_driver()
        now = datetime.now()
        driver.fetch_all = AsyncMock(return_value=[
            {"version": "20240101_000000", "name": "create_users", "applied_at": now},
            {"version": "20240102_000000", "name": "add_email", "applied_at": now},
        ])
        manager = VersionManager(driver)
        conn = MagicMock()

        result = await manager.get_applied(conn)

        assert len(result) == 2
        assert isinstance(result[0], MigrationRecord)
        assert result[0].version == "20240101_000000"
        assert result[1].version == "20240102_000000"

    @pytest.mark.asyncio
    async def test_get_applied_versions(self) -> None:
        """Test get_applied_versions returns set of versions."""
        driver = self.create_mock_driver()
        now = datetime.now()
        driver.fetch_all = AsyncMock(return_value=[
            {"version": "20240101_000000", "name": "create_users", "applied_at": now},
            {"version": "20240102_000000", "name": "add_email", "applied_at": now},
        ])
        manager = VersionManager(driver)
        conn = MagicMock()

        result = await manager.get_applied_versions(conn)

        assert result == {"20240101_000000", "20240102_000000"}

    @pytest.mark.asyncio
    async def test_get_current_version_returns_none_when_empty(self) -> None:
        """Test get_current_version returns None when no migrations."""
        driver = self.create_mock_driver()
        driver.fetch_one = AsyncMock(return_value=None)
        manager = VersionManager(driver)
        conn = MagicMock()

        result = await manager.get_current_version(conn)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_version_returns_latest(self) -> None:
        """Test get_current_version returns latest version."""
        driver = self.create_mock_driver()
        driver.fetch_one = AsyncMock(return_value={"version": "20240102_000000"})
        manager = VersionManager(driver)
        conn = MagicMock()

        result = await manager.get_current_version(conn)

        assert result == "20240102_000000"

    @pytest.mark.asyncio
    async def test_mark_applied_sqlite(self) -> None:
        """Test mark_applied with SQLite driver."""
        driver = self.create_mock_driver("sqlite")
        manager = VersionManager(driver)
        conn = MagicMock()

        await manager.mark_applied(conn, "20240101_000000", "create_users")

        driver.execute.assert_called_once()
        sql, params = driver.execute.call_args[0][1:3]
        assert "INSERT INTO" in sql
        assert "?" in sql
        assert params == ("20240101_000000", "create_users")
        driver.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_applied_postgresql(self) -> None:
        """Test mark_applied with PostgreSQL driver."""
        driver = self.create_mock_driver("postgresql")
        manager = VersionManager(driver)
        conn = MagicMock()

        await manager.mark_applied(conn, "20240101_000000", "create_users")

        sql, params = driver.execute.call_args[0][1:3]
        assert "$1" in sql
        assert "$2" in sql

    @pytest.mark.asyncio
    async def test_mark_applied_mysql(self) -> None:
        """Test mark_applied with MySQL driver."""
        driver = self.create_mock_driver("mysql")
        manager = VersionManager(driver)
        conn = MagicMock()

        await manager.mark_applied(conn, "20240101_000000", "create_users")

        sql, params = driver.execute.call_args[0][1:3]
        assert "%s" in sql

    @pytest.mark.asyncio
    async def test_mark_unapplied_sqlite(self) -> None:
        """Test mark_unapplied with SQLite driver."""
        driver = self.create_mock_driver("sqlite")
        manager = VersionManager(driver)
        conn = MagicMock()

        await manager.mark_unapplied(conn, "20240101_000000")

        driver.execute.assert_called_once()
        sql, params = driver.execute.call_args[0][1:3]
        assert "DELETE FROM" in sql
        assert "?" in sql
        assert params == ("20240101_000000",)

    @pytest.mark.asyncio
    async def test_mark_unapplied_postgresql(self) -> None:
        """Test mark_unapplied with PostgreSQL driver."""
        driver = self.create_mock_driver("postgresql")
        manager = VersionManager(driver)
        conn = MagicMock()

        await manager.mark_unapplied(conn, "20240101_000000")

        sql, _ = driver.execute.call_args[0][1:3]
        assert "$1" in sql

    @pytest.mark.asyncio
    async def test_is_applied_returns_true(self) -> None:
        """Test is_applied returns True when migration exists."""
        driver = self.create_mock_driver()
        driver.fetch_one = AsyncMock(return_value={"1": 1})
        manager = VersionManager(driver)
        conn = MagicMock()

        result = await manager.is_applied(conn, "20240101_000000")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_applied_returns_false(self) -> None:
        """Test is_applied returns False when migration doesn't exist."""
        driver = self.create_mock_driver()
        driver.fetch_one = AsyncMock(return_value=None)
        manager = VersionManager(driver)
        conn = MagicMock()

        result = await manager.is_applied(conn, "20240101_000000")

        assert result is False

    @pytest.mark.asyncio
    async def test_replace_versions(self) -> None:
        """Test replace_versions deletes old and inserts new."""
        driver = self.create_mock_driver("sqlite")
        manager = VersionManager(driver)
        conn = MagicMock()

        await manager.replace_versions(
            conn,
            ["20240101_000000", "20240102_000000"],
            "20240102_000001",
            "squashed_migration",
        )

        # 2 deletes + 1 insert = 3 execute calls
        assert driver.execute.call_count == 3
        driver.commit.assert_called_once()


class TestParseAppliedAt:
    """Tests for _parse_applied_at method."""

    def test_parse_datetime_object(self) -> None:
        """Test parsing datetime object returns as-is."""
        driver = MagicMock()
        driver.driver_name = "sqlite"
        manager = VersionManager(driver)
        now = datetime.now()

        result = manager._parse_applied_at(now, "20240101_000000")

        assert result == now

    def test_parse_iso_string(self) -> None:
        """Test parsing ISO format string."""
        driver = MagicMock()
        driver.driver_name = "sqlite"
        manager = VersionManager(driver)

        result = manager._parse_applied_at("2024-01-15T10:30:00", "20240101_000000")

        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_invalid_string_raises_error(self) -> None:
        """Test parsing invalid string raises ValueError."""
        driver = MagicMock()
        driver.driver_name = "sqlite"
        manager = VersionManager(driver)

        with pytest.raises(ValueError) as exc_info:
            manager._parse_applied_at("not-a-date", "20240101_000000")

        assert "Invalid applied_at format" in str(exc_info.value)
        assert "20240101_000000" in str(exc_info.value)

    def test_parse_invalid_type_raises_error(self) -> None:
        """Test parsing invalid type raises ValueError."""
        driver = MagicMock()
        driver.driver_name = "sqlite"
        manager = VersionManager(driver)

        with pytest.raises(ValueError) as exc_info:
            manager._parse_applied_at(12345, "20240101_000000")

        assert "Invalid applied_at type" in str(exc_info.value)
        assert "int" in str(exc_info.value)
