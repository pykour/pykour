"""Database schema introspection."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pykour.db.migrations.exceptions import SchemaIntrospectionError
from pykour.db.migrations.table import ColumnInfo, IndexDef, TableInfo
from pykour.db.sql_utils import validate_identifier

if TYPE_CHECKING:
    from pykour.db.drivers.base import BaseDriver


class SchemaIntrospector(ABC):
    """Base class for database schema introspection."""

    @abstractmethod
    async def get_tables(self, conn: Any) -> list[str]:
        """Get all table names in the database."""

    @abstractmethod
    async def get_table_info(self, conn: Any, table: str) -> TableInfo:
        """Get detailed information about a table."""

    @abstractmethod
    async def get_indexes(self, conn: Any, table: str) -> list[IndexDef]:
        """Get indexes for a table."""


class SQLiteIntrospector(SchemaIntrospector):
    """SQLite schema introspector."""

    async def get_tables(self, conn: Any) -> list[str]:
        sql = """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name != '_pykour_migrations'
            ORDER BY name
        """
        cursor = await conn.execute(sql)
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    async def get_table_info(self, conn: Any, table: str) -> TableInfo:
        # Validate table name to prevent SQL injection in PRAGMA
        validate_identifier(table, "table", allow_reserved=True)
        sql = f"PRAGMA table_info({table})"
        cursor = await conn.execute(sql)
        rows = await cursor.fetchall()

        columns = []
        primary_key = []

        for row in rows:
            cid, name, type_name, notnull, default, pk = row
            columns.append(
                ColumnInfo(
                    name=name,
                    type=type_name,
                    nullable=not notnull,
                    default=default,
                    primary_key=bool(pk),
                    autoincrement=bool(pk) and type_name.upper() == "INTEGER",
                )
            )
            if pk:
                primary_key.append(name)

        indexes = await self.get_indexes(conn, table)

        return TableInfo(
            name=table,
            columns=columns,
            indexes=indexes,
            primary_key=primary_key,
        )

    async def get_indexes(self, conn: Any, table: str) -> list[IndexDef]:
        # Validate table name to prevent SQL injection in PRAGMA
        validate_identifier(table, "table", allow_reserved=True)
        sql = f"PRAGMA index_list({table})"
        cursor = await conn.execute(sql)
        rows = await cursor.fetchall()

        indexes = []
        for row in rows:
            seq, name, unique, origin, partial = row

            if origin == "pk":
                continue

            # Validate index name before using in PRAGMA
            validate_identifier(name, "index", allow_reserved=True)
            sql2 = f"PRAGMA index_info({name})"
            cursor2 = await conn.execute(sql2)
            cols_rows = await cursor2.fetchall()
            columns = [col_row[2] for col_row in cols_rows]

            indexes.append(
                IndexDef(
                    name=name,
                    table=table,
                    columns=columns,
                    unique=bool(unique),
                )
            )

        return indexes


class PostgreSQLIntrospector(SchemaIntrospector):
    """PostgreSQL schema introspector."""

    async def get_tables(self, conn: Any) -> list[str]:
        sql = """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            AND table_name != '_pykour_migrations'
            ORDER BY table_name
        """
        rows = await conn.fetch(sql)
        return [row["table_name"] for row in rows]

    async def get_table_info(self, conn: Any, table: str) -> TableInfo:
        sql = """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary
            FROM information_schema.columns c
            LEFT JOIN (
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_name = $1
            ) pk ON c.column_name = pk.column_name
            WHERE c.table_name = $1
            AND c.table_schema = 'public'
            ORDER BY c.ordinal_position
        """
        rows = await conn.fetch(sql, table)

        columns = []
        primary_key = []

        for row in rows:
            is_primary = row["is_primary"]
            default = row["column_default"]
            autoincrement = default is not None and "nextval" in str(default).lower()

            columns.append(
                ColumnInfo(
                    name=row["column_name"],
                    type=self._normalize_type(row["data_type"]),
                    nullable=row["is_nullable"] == "YES",
                    default=self._parse_default(default),
                    primary_key=is_primary,
                    autoincrement=autoincrement,
                )
            )
            if is_primary:
                primary_key.append(row["column_name"])

        indexes = await self.get_indexes(conn, table)

        return TableInfo(
            name=table,
            columns=columns,
            indexes=indexes,
            primary_key=primary_key,
        )

    async def get_indexes(self, conn: Any, table: str) -> list[IndexDef]:
        sql = """
            SELECT
                i.relname as index_name,
                ix.indisunique as is_unique,
                array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) as columns
            FROM pg_index ix
            JOIN pg_class i ON ix.indexrelid = i.oid
            JOIN pg_class t ON ix.indrelid = t.oid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relname = $1
            AND NOT ix.indisprimary
            GROUP BY i.relname, ix.indisunique
        """
        rows = await conn.fetch(sql, table)

        return [
            IndexDef(
                name=row["index_name"],
                table=table,
                columns=list(row["columns"]),
                unique=row["is_unique"],
            )
            for row in rows
        ]

    def _normalize_type(self, type_name: str) -> str:
        """Normalize PostgreSQL type names."""
        type_map = {
            "character varying": "VARCHAR",
            "character": "CHAR",
            "integer": "INTEGER",
            "bigint": "BIGINT",
            "smallint": "SMALLINT",
            "boolean": "BOOLEAN",
            "text": "TEXT",
            "timestamp without time zone": "TIMESTAMP",
            "timestamp with time zone": "TIMESTAMPTZ",
            "date": "DATE",
            "time without time zone": "TIME",
            "double precision": "DOUBLE PRECISION",
            "real": "FLOAT",
            "numeric": "DECIMAL",
            "bytea": "BYTEA",
            "json": "JSON",
            "jsonb": "JSONB",
            "uuid": "UUID",
        }
        return type_map.get(type_name.lower(), type_name.upper())

    def _parse_default(self, default: Any) -> Any:
        """Parse PostgreSQL default value.

        Handles PostgreSQL cast syntax like:
        - 'hello'::text -> 'hello'
        - 'hello'::character varying -> 'hello'
        - 123::integer -> '123'
        - true::boolean -> 'true'
        """
        if default is None:
            return None
        default_str = str(default)
        if "nextval" in default_str.lower():
            return None

        # Match quoted values with cast: 'value'::type
        # Type can contain spaces (e.g., "character varying")
        quoted_match = re.match(r"^'(.*)'::[\w\s]+$", default_str)
        if quoted_match:
            return quoted_match.group(1)

        # Match unquoted values with cast: value::type
        # Handles numeric literals, booleans, etc.
        unquoted_match = re.match(r"^(.+)::[\w\s]+$", default_str)
        if unquoted_match:
            return unquoted_match.group(1)

        return default_str


class MySQLIntrospector(SchemaIntrospector):
    """MySQL schema introspector."""

    async def get_tables(self, conn: Any) -> list[str]:
        cursor = await conn.execute("SHOW TABLES")
        rows = await cursor.fetchall()
        tables = [row[0] for row in rows if row[0] != "_pykour_migrations"]
        return sorted(tables)

    async def get_table_info(self, conn: Any, table: str) -> TableInfo:
        # Validate table name to prevent SQL injection
        validate_identifier(table, "table", allow_reserved=True)
        cursor = await conn.execute(f"DESCRIBE `{table}`")
        rows = await cursor.fetchall()

        columns = []
        primary_key = []

        for row in rows:
            field, type_name, null, key, default, extra = row
            is_primary = key == "PRI"
            autoincrement = "auto_increment" in str(extra).lower()

            columns.append(
                ColumnInfo(
                    name=field,
                    type=self._normalize_type(type_name),
                    nullable=null == "YES",
                    default=default,
                    primary_key=is_primary,
                    autoincrement=autoincrement,
                )
            )
            if is_primary:
                primary_key.append(field)

        indexes = await self.get_indexes(conn, table)

        return TableInfo(
            name=table,
            columns=columns,
            indexes=indexes,
            primary_key=primary_key,
        )

    async def get_indexes(self, conn: Any, table: str) -> list[IndexDef]:
        # Validate table name to prevent SQL injection
        validate_identifier(table, "table", allow_reserved=True)
        cursor = await conn.execute(f"SHOW INDEX FROM `{table}`")
        rows = await cursor.fetchall()

        index_map: dict[str, IndexDef] = {}
        for row in rows:
            non_unique, key_name, _, column_name = row[1], row[2], row[3], row[4]

            if key_name == "PRIMARY":
                continue

            if key_name not in index_map:
                index_map[key_name] = IndexDef(
                    name=key_name,
                    table=table,
                    columns=[],
                    unique=not non_unique,
                )
            index_map[key_name].columns.append(column_name)

        return list(index_map.values())

    def _normalize_type(self, type_name: str) -> str:
        """Normalize MySQL type names."""
        type_upper = type_name.upper()
        if type_upper.startswith("INT"):
            return "INTEGER"
        if type_upper.startswith("TINYINT(1)"):
            return "BOOLEAN"
        if type_upper.startswith("VARCHAR"):
            return type_upper
        if type_upper.startswith("CHAR"):
            return type_upper
        return type_upper


def get_introspector(driver: BaseDriver) -> SchemaIntrospector:
    """Get the appropriate introspector for a driver."""
    class_name = driver.__class__.__name__.lower()

    if "sqlite" in class_name:
        return SQLiteIntrospector()
    if "postgresql" in class_name or "postgres" in class_name:
        return PostgreSQLIntrospector()
    if "mysql" in class_name:
        return MySQLIntrospector()

    raise SchemaIntrospectionError(f"Unknown driver: {driver.__class__.__name__}")
