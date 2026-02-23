"""Tests for migration operations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pykour.db.migrations.operations import (
    AddColumn,
    AlterColumn,
    CreateIndex,
    CreateTable,
    DropColumn,
    DropIndex,
    DropTable,
    ExecuteSQL,
    RenameColumn,
    RenameTable,
)
from pykour.db.migrations.table import ColumnDef, ColumnInfo, IndexDef, TableInfo


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_sqlite_driver() -> MagicMock:
    driver = MagicMock()
    driver.driver_name = "sqlite"
    driver.__class__ = type("SQLiteDriver", (), {})
    return driver


def _make_mysql_driver() -> MagicMock:
    driver = MagicMock()
    driver.driver_name = "mysql"
    driver.__class__ = type("MySQLDriver", (), {})
    return driver


def _make_postgresql_driver() -> MagicMock:
    driver = MagicMock()
    driver.driver_name = "postgresql"
    driver.__class__ = type("PostgreSQLDriver", (), {})
    return driver


def _make_conn() -> AsyncMock:
    return AsyncMock()


def _make_table_info(
    columns: list[ColumnInfo], indexes: list[IndexDef] | None = None
) -> TableInfo:
    return TableInfo(
        name="users",
        columns=columns,
        indexes=indexes or [],
        primary_key=[c.name for c in columns if c.primary_key],
    )


class TestCreateTable:
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


class TestDropTable:
    """Tests for DropTable operation."""

    def test_to_code(self) -> None:
        """DropTable should generate correct Python code."""
        op = DropTable("users")
        code = op.to_code()

        assert 'op.drop_table("users")' == code


class TestAddColumn:
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


class TestDropColumn:
    """Tests for DropColumn operation."""

    def test_to_code(self) -> None:
        """DropColumn should generate correct Python code."""
        op = DropColumn("users", "email")
        code = op.to_code()

        assert 'op.drop_column("users", "email")' == code


class TestAlterColumn:
    """Tests for AlterColumn operation."""

    # ------------------------------------------------------------------
    # SQLite tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_sqlite_alter_type(self) -> None:
        """AlterColumn with new_type should rebuild the SQLite table with the new type."""
        driver = _make_sqlite_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("name", "VARCHAR(100)", nullable=False),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "name", new_type="TEXT")
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert any("PRAGMA foreign_keys = OFF" in s for s in sqls)
        assert any("CREATE TABLE" in s and "TEXT" in s for s in sqls)
        assert any("INSERT INTO" in s for s in sqls)
        assert any("DROP TABLE" in s for s in sqls)
        assert any("RENAME TO" in s for s in sqls)
        assert any("PRAGMA foreign_keys = ON" in s for s in sqls)

    @pytest.mark.asyncio
    async def test_sqlite_alter_nullable(self) -> None:
        """AlterColumn with nullable=False should add NOT NULL in the rebuilt table."""
        driver = _make_sqlite_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("age", "INTEGER", nullable=True),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "age", nullable=False)
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        create_sql = next(s for s in sqls if "CREATE TABLE" in s)
        assert "NOT NULL" in create_sql

    @pytest.mark.asyncio
    async def test_sqlite_alter_new_default(self) -> None:
        """AlterColumn with new_default should include DEFAULT in the rebuilt table."""
        driver = _make_sqlite_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("score", "INTEGER", nullable=True),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "score", new_default=0)
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        create_sql = next(s for s in sqls if "CREATE TABLE" in s)
        assert "DEFAULT 0" in create_sql

    @pytest.mark.asyncio
    async def test_sqlite_drop_default(self) -> None:
        """AlterColumn with drop_default=True should omit DEFAULT in the rebuilt table."""
        driver = _make_sqlite_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("score", "INTEGER", nullable=True, default="0"),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "score", drop_default=True)
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        create_sql = next(s for s in sqls if "CREATE TABLE" in s)
        assert "DEFAULT" not in create_sql

    @pytest.mark.asyncio
    async def test_sqlite_with_indexes(self) -> None:
        """AlterColumn should recreate indexes after table rebuild."""
        driver = _make_sqlite_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            columns=[
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("email", "VARCHAR(255)", nullable=False),
            ],
            indexes=[IndexDef("idx_users_email", "users", ["email"], unique=True)],
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "email", new_type="TEXT")
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert any("CREATE UNIQUE INDEX idx_users_email" in s for s in sqls)

    @pytest.mark.asyncio
    async def test_sqlite_column_not_found(self) -> None:
        """AlterColumn should raise ValueError when the column does not exist."""
        driver = _make_sqlite_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True)]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "nonexistent", new_type="TEXT")
            with pytest.raises(ValueError, match="nonexistent"):
                await op.execute(driver, conn)

    # ------------------------------------------------------------------
    # MySQL tests
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_mysql_alter_nullable(self) -> None:
        """MySQL AlterColumn with nullable=False should succeed (no NotImplementedError)."""
        driver = _make_mysql_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("name", "VARCHAR(100)", nullable=True),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "name", nullable=False)
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert len(sqls) == 1
        assert "MODIFY COLUMN" in sqls[0]
        assert "NOT NULL" in sqls[0]

    @pytest.mark.asyncio
    async def test_mysql_alter_default(self) -> None:
        """MySQL AlterColumn with new_default should succeed (no NotImplementedError)."""
        driver = _make_mysql_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("score", "INTEGER", nullable=True),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "score", new_default=0)
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert "MODIFY COLUMN" in sqls[0]
        assert "DEFAULT 0" in sqls[0]

    @pytest.mark.asyncio
    async def test_mysql_drop_default(self) -> None:
        """MySQL AlterColumn with drop_default=True should omit DEFAULT in MODIFY COLUMN."""
        driver = _make_mysql_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("score", "INTEGER", nullable=True, default="42"),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "score", drop_default=True)
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert "MODIFY COLUMN" in sqls[0]
        assert "DEFAULT" not in sqls[0]

    @pytest.mark.asyncio
    async def test_mysql_alter_type_and_nullable(self) -> None:
        """MySQL AlterColumn with new_type and nullable should generate a correct MODIFY COLUMN."""
        driver = _make_mysql_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("age", "INTEGER", nullable=True),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "age", new_type="BIGINT", nullable=False)
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert "BIGINT" in sqls[0]
        assert "NOT NULL" in sqls[0]

    @pytest.mark.asyncio
    async def test_mysql_column_not_found(self) -> None:
        """MySQL AlterColumn should raise ValueError when the column does not exist."""
        driver = _make_mysql_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True)]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = AlterColumn("users", "nonexistent", nullable=False)
            with pytest.raises(ValueError, match="nonexistent"):
                await op.execute(driver, conn)

    # ------------------------------------------------------------------
    # PostgreSQL tests (confirm existing behavior is preserved)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_postgresql_alter_type(self) -> None:
        """PostgreSQL AlterColumn with new_type should execute ALTER COLUMN TYPE."""
        driver = _make_postgresql_driver()
        conn = _make_conn()
        op = AlterColumn("users", "name", new_type="TEXT")
        await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert any("ALTER COLUMN name TYPE TEXT" in s for s in sqls)

    @pytest.mark.asyncio
    async def test_postgresql_alter_nullable_drop(self) -> None:
        """PostgreSQL AlterColumn nullable=True should execute DROP NOT NULL."""
        driver = _make_postgresql_driver()
        conn = _make_conn()
        op = AlterColumn("users", "name", nullable=True)
        await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert any("DROP NOT NULL" in s for s in sqls)

    @pytest.mark.asyncio
    async def test_postgresql_alter_nullable_set(self) -> None:
        """PostgreSQL AlterColumn nullable=False should execute SET NOT NULL."""
        driver = _make_postgresql_driver()
        conn = _make_conn()
        op = AlterColumn("users", "name", nullable=False)
        await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert any("SET NOT NULL" in s for s in sqls)

    @pytest.mark.asyncio
    async def test_postgresql_alter_default(self) -> None:
        """PostgreSQL AlterColumn with new_default should execute SET DEFAULT."""
        driver = _make_postgresql_driver()
        conn = _make_conn()
        op = AlterColumn("users", "score", new_default=42)
        await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert any("SET DEFAULT 42" in s for s in sqls)

    # ------------------------------------------------------------------
    # Meta tests
    # ------------------------------------------------------------------

    def test_to_code(self) -> None:
        """AlterColumn.to_code() should generate correct Python code."""
        op = AlterColumn("users", "name", new_type="TEXT", nullable=False)
        code = op.to_code()
        assert 'op.alter_column("users", "name"' in code
        assert 'new_type="TEXT"' in code
        assert "nullable=False" in code

    def test_reverse(self) -> None:
        """AlterColumn.reverse() should return an inverse operation."""
        op = AlterColumn(
            "users",
            "name",
            new_type="TEXT",
            _old_type="VARCHAR(100)",
        )
        reverse = op.reverse()
        assert isinstance(reverse, AlterColumn)
        assert reverse.new_type == "VARCHAR(100)"


class TestRenameTable:
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


class TestRenameColumn:
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

    @pytest.mark.asyncio
    async def test_rename_column_mysql(self) -> None:
        """RenameColumn on MySQL should use CHANGE COLUMN syntax."""
        driver = _make_mysql_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("name", "VARCHAR(100)", nullable=False),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = RenameColumn("users", "name", "full_name")
            await op.execute(driver, conn)

        sqls = [call.args[0] for call in conn.execute.call_args_list]
        assert len(sqls) == 1
        assert "CHANGE COLUMN" in sqls[0]
        assert "`name`" in sqls[0]
        assert "`full_name`" in sqls[0]

    @pytest.mark.asyncio
    async def test_rename_column_mysql_preserves_definition(self) -> None:
        """MySQL RenameColumn should preserve type, nullable, and default."""
        driver = _make_mysql_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [
                ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True),
                ColumnInfo("score", "INTEGER", nullable=True, default="10"),
            ]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = RenameColumn("users", "score", "points")
            await op.execute(driver, conn)

        sql = conn.execute.call_args_list[0].args[0]
        assert "INTEGER" in sql
        assert "NULL" in sql
        assert "DEFAULT 10" in sql

    @pytest.mark.asyncio
    async def test_rename_column_mysql_column_not_found(self) -> None:
        """MySQL RenameColumn should raise ValueError when the column does not exist."""
        driver = _make_mysql_driver()
        conn = _make_conn()
        table_info = _make_table_info(
            [ColumnInfo("id", "INTEGER", primary_key=True, autoincrement=True)]
        )

        with patch("pykour.db.migrations.operations.get_introspector") as mock_gi:
            mock_gi.return_value.get_table_info = AsyncMock(return_value=table_info)
            op = RenameColumn("users", "nonexistent", "new_name")
            with pytest.raises(ValueError, match="nonexistent"):
                await op.execute(driver, conn)


class TestCreateIndex:
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


class TestDropIndex:
    """Tests for DropIndex operation."""

    def test_to_code(self) -> None:
        """DropIndex should generate correct Python code."""
        op = DropIndex("idx_users_email")
        code = op.to_code()

        assert 'op.drop_index("idx_users_email")' == code


class TestExecuteSQL:
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
