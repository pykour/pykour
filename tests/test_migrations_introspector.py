"""Tests for database schema introspection."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pykour.db.migrations.exceptions import SchemaIntrospectionError
from pykour.db.migrations.introspector import (
    MySQLIntrospector,
    PostgreSQLIntrospector,
    SQLiteIntrospector,
    get_introspector,
)
from pykour.db.migrations.table import ColumnInfo, IndexDef, TableInfo


class TestSQLiteIntrospector:
    """Tests for SQLiteIntrospector class."""

    @pytest.mark.asyncio
    async def test_get_tables(self) -> None:
        """Test get_tables returns table names."""
        introspector = SQLiteIntrospector()
        conn = MagicMock()
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(
            return_value=[
                ("users",),
                ("orders",),
            ]
        )
        conn.execute = AsyncMock(return_value=cursor)

        result = await introspector.get_tables(conn)

        assert result == ["users", "orders"]

    @pytest.mark.asyncio
    async def test_get_tables_excludes_system_tables(self) -> None:
        """Test get_tables excludes SQLite system tables."""
        introspector = SQLiteIntrospector()
        conn = MagicMock()
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(
            return_value=[
                ("users",),
            ]
        )
        conn.execute = AsyncMock(return_value=cursor)

        await introspector.get_tables(conn)

        sql = conn.execute.call_args[0][0]
        assert "sqlite_%" in sql
        assert "_pykour_migrations" in sql

    @pytest.mark.asyncio
    async def test_get_table_info(self) -> None:
        """Test get_table_info returns TableInfo."""
        introspector = SQLiteIntrospector()
        conn = MagicMock()

        # Mock for PRAGMA table_info
        table_cursor = AsyncMock()
        table_cursor.fetchall = AsyncMock(
            return_value=[
                (0, "id", "INTEGER", 0, None, 1),
                (1, "name", "TEXT", 1, None, 0),
                (2, "email", "TEXT", 0, "'guest@example.com'", 0),
            ]
        )

        # Mock for PRAGMA index_list
        index_cursor = AsyncMock()
        index_cursor.fetchall = AsyncMock(return_value=[])

        async def mock_execute(sql: str) -> Any:
            if "table_info" in sql:
                return table_cursor
            elif "index_list" in sql:
                return index_cursor
            return AsyncMock()

        conn.execute = mock_execute

        result = await introspector.get_table_info(conn, "users")

        assert isinstance(result, TableInfo)
        assert result.name == "users"
        assert len(result.columns) == 3
        assert result.columns[0].name == "id"
        assert result.columns[0].primary_key is True
        assert result.columns[0].autoincrement is True
        assert result.columns[1].name == "name"
        assert result.columns[1].nullable is False
        assert result.columns[2].default == "'guest@example.com'"

    @pytest.mark.asyncio
    async def test_get_indexes(self) -> None:
        """Test get_indexes returns index definitions."""
        introspector = SQLiteIntrospector()
        conn = MagicMock()

        # Mock for PRAGMA index_list
        index_list_cursor = AsyncMock()
        index_list_cursor.fetchall = AsyncMock(
            return_value=[
                (0, "idx_email", 1, "c", 0),  # unique index
            ]
        )

        # Mock for PRAGMA index_info
        index_info_cursor = AsyncMock()
        index_info_cursor.fetchall = AsyncMock(
            return_value=[
                (0, 2, "email"),  # column at position 2, name "email"
            ]
        )

        async def mock_execute(sql: str) -> Any:
            if "index_list" in sql:
                return index_list_cursor
            elif "index_info" in sql:
                return index_info_cursor
            return AsyncMock()

        conn.execute = mock_execute

        result = await introspector.get_indexes(conn, "users")

        assert len(result) == 1
        assert result[0].name == "idx_email"
        assert result[0].columns == ["email"]
        assert result[0].unique is True

    @pytest.mark.asyncio
    async def test_get_indexes_skips_primary_key(self) -> None:
        """Test get_indexes skips primary key indexes."""
        introspector = SQLiteIntrospector()
        conn = MagicMock()

        # Mock for PRAGMA index_list with pk origin
        index_list_cursor = AsyncMock()
        index_list_cursor.fetchall = AsyncMock(
            return_value=[
                (0, "sqlite_autoindex_users_1", 1, "pk", 0),  # primary key
            ]
        )

        conn.execute = AsyncMock(return_value=index_list_cursor)

        result = await introspector.get_indexes(conn, "users")

        assert len(result) == 0


class TestPostgreSQLIntrospector:
    """Tests for PostgreSQLIntrospector class."""

    @pytest.mark.asyncio
    async def test_get_tables(self) -> None:
        """Test get_tables returns table names."""
        introspector = PostgreSQLIntrospector()
        conn = MagicMock()
        conn.fetch = AsyncMock(
            return_value=[
                {"table_name": "orders"},
                {"table_name": "users"},
            ]
        )

        result = await introspector.get_tables(conn)

        assert result == ["orders", "users"]

    @pytest.mark.asyncio
    async def test_get_table_info(self) -> None:
        """Test get_table_info returns TableInfo."""
        introspector = PostgreSQLIntrospector()
        conn = MagicMock()

        # Mock for column info query
        column_data = [
            {
                "column_name": "id",
                "data_type": "integer",
                "is_nullable": "NO",
                "column_default": "nextval('users_id_seq'::regclass)",
                "is_primary": True,
            },
            {
                "column_name": "name",
                "data_type": "character varying",
                "is_nullable": "YES",
                "column_default": None,
                "is_primary": False,
            },
        ]

        # Mock for index query
        index_data: list[dict[str, Any]] = []

        async def mock_fetch(sql: str, *args: Any) -> list[dict[str, Any]]:
            if "information_schema.columns" in sql:
                return column_data
            elif "pg_index" in sql:
                return index_data
            return []

        conn.fetch = mock_fetch

        result = await introspector.get_table_info(conn, "users")

        assert isinstance(result, TableInfo)
        assert result.name == "users"
        assert len(result.columns) == 2
        assert result.columns[0].name == "id"
        assert result.columns[0].type == "INTEGER"
        assert result.columns[0].autoincrement is True
        assert result.columns[1].name == "name"
        assert result.columns[1].type == "VARCHAR"

    @pytest.mark.asyncio
    async def test_get_indexes(self) -> None:
        """Test get_indexes returns index definitions."""
        introspector = PostgreSQLIntrospector()
        conn = MagicMock()
        conn.fetch = AsyncMock(
            return_value=[
                {
                    "index_name": "idx_users_email",
                    "is_unique": True,
                    "columns": ["email"],
                },
            ]
        )

        result = await introspector.get_indexes(conn, "users")

        assert len(result) == 1
        assert result[0].name == "idx_users_email"
        assert result[0].columns == ["email"]
        assert result[0].unique is True

    def test_normalize_type_character_varying(self) -> None:
        """Test _normalize_type handles character varying."""
        introspector = PostgreSQLIntrospector()
        assert introspector._normalize_type("character varying") == "VARCHAR"

    def test_normalize_type_integer(self) -> None:
        """Test _normalize_type handles integer."""
        introspector = PostgreSQLIntrospector()
        assert introspector._normalize_type("integer") == "INTEGER"

    def test_normalize_type_timestamp(self) -> None:
        """Test _normalize_type handles timestamp types."""
        introspector = PostgreSQLIntrospector()
        assert (
            introspector._normalize_type("timestamp without time zone") == "TIMESTAMP"
        )
        assert introspector._normalize_type("timestamp with time zone") == "TIMESTAMPTZ"

    def test_normalize_type_json(self) -> None:
        """Test _normalize_type handles JSON types."""
        introspector = PostgreSQLIntrospector()
        assert introspector._normalize_type("json") == "JSON"
        assert introspector._normalize_type("jsonb") == "JSONB"

    def test_normalize_type_unknown(self) -> None:
        """Test _normalize_type handles unknown types."""
        introspector = PostgreSQLIntrospector()
        assert introspector._normalize_type("custom_type") == "CUSTOM_TYPE"

    def test_parse_default_none(self) -> None:
        """Test _parse_default handles None."""
        introspector = PostgreSQLIntrospector()
        assert introspector._parse_default(None) is None

    def test_parse_default_nextval(self) -> None:
        """Test _parse_default handles nextval (sequence)."""
        introspector = PostgreSQLIntrospector()
        assert introspector._parse_default("nextval('users_id_seq'::regclass)") is None

    def test_parse_default_quoted_string_with_cast(self) -> None:
        """Test _parse_default handles quoted string with cast."""
        introspector = PostgreSQLIntrospector()
        assert introspector._parse_default("'hello'::text") == "hello"
        assert introspector._parse_default("'world'::character varying") == "world"

    def test_parse_default_unquoted_with_cast(self) -> None:
        """Test _parse_default handles unquoted values with cast."""
        introspector = PostgreSQLIntrospector()
        assert introspector._parse_default("123::integer") == "123"
        assert introspector._parse_default("true::boolean") == "true"

    def test_parse_default_plain_string(self) -> None:
        """Test _parse_default handles plain strings."""
        introspector = PostgreSQLIntrospector()
        assert introspector._parse_default("some_value") == "some_value"


class TestMySQLIntrospector:
    """Tests for MySQLIntrospector class."""

    @pytest.mark.asyncio
    async def test_get_tables(self) -> None:
        """Test get_tables returns table names."""
        introspector = MySQLIntrospector()
        conn = MagicMock()
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(
            return_value=[
                ("users",),
                ("orders",),
            ]
        )
        conn.execute = AsyncMock(return_value=cursor)

        result = await introspector.get_tables(conn)

        assert result == ["orders", "users"]  # sorted

    @pytest.mark.asyncio
    async def test_get_tables_excludes_migrations_table(self) -> None:
        """Test get_tables excludes _pykour_migrations."""
        introspector = MySQLIntrospector()
        conn = MagicMock()
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(
            return_value=[
                ("users",),
                ("_pykour_migrations",),
            ]
        )
        conn.execute = AsyncMock(return_value=cursor)

        result = await introspector.get_tables(conn)

        assert "_pykour_migrations" not in result
        assert result == ["users"]

    @pytest.mark.asyncio
    async def test_get_table_info(self) -> None:
        """Test get_table_info returns TableInfo."""
        introspector = MySQLIntrospector()
        conn = MagicMock()

        # Mock for DESCRIBE
        describe_cursor = AsyncMock()
        describe_cursor.fetchall = AsyncMock(
            return_value=[
                ("id", "int(11)", "NO", "PRI", None, "auto_increment"),
                ("name", "varchar(255)", "YES", "", None, ""),
            ]
        )

        # Mock for SHOW INDEX
        index_cursor = AsyncMock()
        index_cursor.fetchall = AsyncMock(return_value=[])

        async def mock_execute(sql: str) -> Any:
            if "DESCRIBE" in sql:
                return describe_cursor
            elif "SHOW INDEX" in sql:
                return index_cursor
            return AsyncMock()

        conn.execute = mock_execute

        result = await introspector.get_table_info(conn, "users")

        assert isinstance(result, TableInfo)
        assert result.name == "users"
        assert len(result.columns) == 2
        assert result.columns[0].name == "id"
        assert result.columns[0].type == "INTEGER"
        assert result.columns[0].primary_key is True
        assert result.columns[0].autoincrement is True
        assert result.columns[1].name == "name"
        assert result.columns[1].type == "VARCHAR(255)"

    @pytest.mark.asyncio
    async def test_get_indexes(self) -> None:
        """Test get_indexes returns index definitions."""
        introspector = MySQLIntrospector()
        conn = MagicMock()
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(
            return_value=[
                # (Table, Non_unique, Key_name, Seq_in_index, Column_name, ...)
                (
                    "users",
                    0,
                    "idx_email",
                    1,
                    "email",
                    None,
                    None,
                    None,
                    None,
                    "",
                    "",
                    "",
                    "",
                ),
            ]
        )
        conn.execute = AsyncMock(return_value=cursor)

        result = await introspector.get_indexes(conn, "users")

        assert len(result) == 1
        assert result[0].name == "idx_email"
        assert result[0].columns == ["email"]
        assert result[0].unique is True

    @pytest.mark.asyncio
    async def test_get_indexes_skips_primary_key(self) -> None:
        """Test get_indexes skips PRIMARY key."""
        introspector = MySQLIntrospector()
        conn = MagicMock()
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(
            return_value=[
                (
                    "users",
                    0,
                    "PRIMARY",
                    1,
                    "id",
                    None,
                    None,
                    None,
                    None,
                    "",
                    "",
                    "",
                    "",
                ),
            ]
        )
        conn.execute = AsyncMock(return_value=cursor)

        result = await introspector.get_indexes(conn, "users")

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_indexes_composite(self) -> None:
        """Test get_indexes handles composite indexes."""
        introspector = MySQLIntrospector()
        conn = MagicMock()
        cursor = AsyncMock()
        cursor.fetchall = AsyncMock(
            return_value=[
                (
                    "users",
                    1,
                    "idx_name_email",
                    1,
                    "name",
                    None,
                    None,
                    None,
                    None,
                    "",
                    "",
                    "",
                    "",
                ),
                (
                    "users",
                    1,
                    "idx_name_email",
                    2,
                    "email",
                    None,
                    None,
                    None,
                    None,
                    "",
                    "",
                    "",
                    "",
                ),
            ]
        )
        conn.execute = AsyncMock(return_value=cursor)

        result = await introspector.get_indexes(conn, "users")

        assert len(result) == 1
        assert result[0].name == "idx_name_email"
        assert result[0].columns == ["name", "email"]
        assert result[0].unique is False

    def test_normalize_type_int(self) -> None:
        """Test _normalize_type handles INT variants."""
        introspector = MySQLIntrospector()
        assert introspector._normalize_type("int(11)") == "INTEGER"
        assert introspector._normalize_type("INT") == "INTEGER"

    def test_normalize_type_tinyint_boolean(self) -> None:
        """Test _normalize_type handles TINYINT(1) as BOOLEAN."""
        introspector = MySQLIntrospector()
        assert introspector._normalize_type("tinyint(1)") == "BOOLEAN"

    def test_normalize_type_varchar(self) -> None:
        """Test _normalize_type preserves VARCHAR with length."""
        introspector = MySQLIntrospector()
        assert introspector._normalize_type("varchar(255)") == "VARCHAR(255)"

    def test_normalize_type_char(self) -> None:
        """Test _normalize_type preserves CHAR with length."""
        introspector = MySQLIntrospector()
        assert introspector._normalize_type("char(10)") == "CHAR(10)"


class TestGetIntrospector:
    """Tests for get_introspector factory function."""

    def test_returns_sqlite_introspector(self) -> None:
        """Test returns SQLiteIntrospector for SQLite driver."""
        driver = MagicMock()
        driver.__class__.__name__ = "SQLiteDriver"

        result = get_introspector(driver)

        assert isinstance(result, SQLiteIntrospector)

    def test_returns_postgresql_introspector(self) -> None:
        """Test returns PostgreSQLIntrospector for PostgreSQL driver."""
        driver = MagicMock()
        driver.__class__.__name__ = "PostgreSQLDriver"

        result = get_introspector(driver)

        assert isinstance(result, PostgreSQLIntrospector)

    def test_returns_postgresql_introspector_for_postgres(self) -> None:
        """Test returns PostgreSQLIntrospector for Postgres name variant."""
        driver = MagicMock()
        driver.__class__.__name__ = "PostgresDriver"

        result = get_introspector(driver)

        assert isinstance(result, PostgreSQLIntrospector)

    def test_returns_mysql_introspector(self) -> None:
        """Test returns MySQLIntrospector for MySQL driver."""
        driver = MagicMock()
        driver.__class__.__name__ = "MySQLDriver"

        result = get_introspector(driver)

        assert isinstance(result, MySQLIntrospector)

    def test_raises_for_unknown_driver(self) -> None:
        """Test raises SchemaIntrospectionError for unknown driver."""
        driver = MagicMock()
        driver.__class__.__name__ = "UnknownDriver"

        with pytest.raises(SchemaIntrospectionError) as exc_info:
            get_introspector(driver)

        assert "Unknown driver" in str(exc_info.value)


class TestColumnInfo:
    """Tests for ColumnInfo dataclass."""

    def test_create_column_info(self) -> None:
        """Test creating ColumnInfo."""
        col = ColumnInfo(
            name="id",
            type="INTEGER",
            nullable=False,
            default=None,
            primary_key=True,
            autoincrement=True,
        )
        assert col.name == "id"
        assert col.type == "INTEGER"
        assert col.nullable is False
        assert col.primary_key is True
        assert col.autoincrement is True


class TestIndexDef:
    """Tests for IndexDef dataclass."""

    def test_create_index_def(self) -> None:
        """Test creating IndexDef."""
        idx = IndexDef(
            name="idx_email",
            table="users",
            columns=["email"],
            unique=True,
        )
        assert idx.name == "idx_email"
        assert idx.table == "users"
        assert idx.columns == ["email"]
        assert idx.unique is True


class TestTableInfo:
    """Tests for TableInfo dataclass."""

    def test_create_table_info(self) -> None:
        """Test creating TableInfo."""
        columns = [
            ColumnInfo("id", "INTEGER", False, None, True, True),
            ColumnInfo("name", "TEXT", True, None, False, False),
        ]
        indexes = [IndexDef("idx_name", "users", ["name"], False)]

        table = TableInfo(
            name="users",
            columns=columns,
            indexes=indexes,
            primary_key=["id"],
        )

        assert table.name == "users"
        assert len(table.columns) == 2
        assert len(table.indexes) == 1
        assert table.primary_key == ["id"]
