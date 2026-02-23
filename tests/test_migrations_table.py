"""Tests for migration table and column definitions."""

from pykour.db.access_policy import AccessPolicy
from pykour.db.migrations.table import Column, ColumnDef, IndexDef, Table
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


class TestIndexDef:
    """Tests for IndexDef class."""

    def test_basic_index_def(self) -> None:
        """Basic IndexDef should have correct defaults."""
        idx = IndexDef(name="idx_test", table="test", columns=["email"])
        assert idx.columns == ["email"]
        assert idx.unique is False
        assert idx.where is None
        assert idx.name == "idx_test"

    def test_unique_index_def(self) -> None:
        """Unique IndexDef should have correct settings."""
        idx = IndexDef(name="uq_test", table="test", columns=["email"], unique=True)
        assert idx.unique is True

    def test_partial_index_def(self) -> None:
        """Partial IndexDef should store WHERE clause."""
        idx = IndexDef(
            name="idx_test", table="test", columns=["email"], where="active = 1"
        )
        assert idx.where == "active = 1"

    def test_composite_index_def(self) -> None:
        """Composite IndexDef should store multiple columns."""
        idx = IndexDef(name="idx_test", table="test", columns=["name", "created_at"])
        assert idx.columns == ["name", "created_at"]


class TestTableWithMeta:
    """Tests for Table class with Meta inner class."""

    def test_table_with_unique_together(self) -> None:
        """Table should collect unique_together from Meta class."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)
            email = Column(String(255))
            domain = Column(String(100))

            class Meta:
                unique_together = [("email", "domain")]

        unique = UserTable.get_unique_together()
        assert len(unique) == 1
        assert unique[0] == ("email", "domain")

        # Should generate unique index
        indexes = UserTable.get_indexes()
        assert len(indexes) == 1
        assert indexes[0].name == "uq_users_email_domain"
        assert indexes[0].columns == ["email", "domain"]
        assert indexes[0].unique is True

    def test_table_with_search_keys(self) -> None:
        """Table should collect search_keys from Meta class."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)
            tenant_id = Column(String(36))
            email = Column(String(255))
            created_at = Column(DateTime())

            class Meta:
                search_keys = [["tenant_id"], ["email", "created_at"]]

        search_keys = UserTable.get_search_keys()
        assert len(search_keys) == 2
        assert search_keys[0] == ["tenant_id"]
        assert search_keys[1] == ["email", "created_at"]

        # Should generate non-unique indexes
        indexes = UserTable.get_indexes()
        assert len(indexes) == 2
        assert indexes[0].name == "idx_users_tenant_id"
        assert indexes[0].columns == ["tenant_id"]
        assert indexes[0].unique is False
        assert indexes[1].name == "idx_users_email_created_at"
        assert indexes[1].columns == ["email", "created_at"]
        assert indexes[1].unique is False

    def test_table_with_meta_access_policy(self) -> None:
        """Table should collect access_policy from Meta class."""

        class OrderTable(Table):
            __tablename__ = "orders"
            id = Column(Integer(), primary_key=True)
            tenant_id = Column(String(36))

            class Meta:
                access_policy = AccessPolicy(
                    select=["tenant_id = :tenant_id"],
                    insert=["tenant_id = :tenant_id"],
                    auto_set={"tenant_id": ":tenant_id"},
                )

        policy = OrderTable.get_access_policy()
        assert policy is not None
        assert policy.select == ["tenant_id = :tenant_id"]
        assert policy.insert == ["tenant_id = :tenant_id"]
        assert policy.auto_set == {"tenant_id": ":tenant_id"}

    def test_table_with_legacy_access_policy(self) -> None:
        """Table should still support __access_policy__ attribute."""

        class OrderTable(Table):
            __tablename__ = "orders"
            __access_policy__ = AccessPolicy(
                select=["tenant_id = :tenant_id"],
            )
            id = Column(Integer(), primary_key=True)
            tenant_id = Column(String(36))

        policy = OrderTable.get_access_policy()
        assert policy is not None
        assert policy.select == ["tenant_id = :tenant_id"]

    def test_meta_access_policy_takes_precedence(self) -> None:
        """Meta.access_policy should take precedence over __access_policy__."""

        class OrderTable(Table):
            __tablename__ = "orders"
            __access_policy__ = AccessPolicy(
                select=["old = :old"],
            )
            id = Column(Integer(), primary_key=True)
            tenant_id = Column(String(36))

            class Meta:
                access_policy = AccessPolicy(
                    select=["new = :new"],
                )

        policy = OrderTable.get_access_policy()
        assert policy is not None
        assert policy.select == ["new = :new"]

    def test_table_with_combined_meta(self) -> None:
        """Table should handle all Meta options together."""

        class OrderTable(Table):
            __tablename__ = "orders"
            id = Column(Integer(), primary_key=True)
            tenant_id = Column(String(36))
            user_id = Column(String(36))
            email = Column(String(255))
            domain = Column(String(100))

            class Meta:
                unique_together = [("email", "domain"), ("tenant_id", "email")]
                search_keys = [["tenant_id"], ["user_id"]]
                access_policy = AccessPolicy(
                    select=["tenant_id = :tenant_id"],
                )

        unique = OrderTable.get_unique_together()
        assert len(unique) == 2

        search_keys = OrderTable.get_search_keys()
        assert len(search_keys) == 2

        indexes = OrderTable.get_indexes()
        assert len(indexes) == 4  # 2 unique + 2 search

        policy = OrderTable.get_access_policy()
        assert policy is not None

    def test_table_without_meta(self) -> None:
        """Table without Meta should have empty indexes and no policy."""

        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)

        assert UserTable.get_unique_together() == []
        assert UserTable.get_search_keys() == []
        assert UserTable.get_indexes() == []
        assert UserTable.get_access_policy() is None
