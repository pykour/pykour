"""Tests for migration table and column definitions."""

from pykour.db.migrations.table import Column, ColumnDef, Index, Table
from pykour.db.migrations.types import Boolean, DateTime, Integer, String


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
