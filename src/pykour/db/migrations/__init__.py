"""Database migrations module.

Example usage:

    # Define a table with indexes using Meta class
    from pykour.db.migrations import Table, Column, Integer, String, Boolean

    class UserTable(Table):
        __tablename__ = "users"

        id = Column(Integer(), primary_key=True, autoincrement=True)
        name = Column(String(100), nullable=False)
        email = Column(String(255), unique=True, nullable=False)
        active = Column(Boolean(), default=True)

        class Meta:
            # Unique constraint (creates UNIQUE INDEX)
            unique_together = [
                ("email",),  # Single column unique
            ]

            # Search keys (creates INDEX)
            search_keys = [
                ["email"],  # For fast email lookups
            ]

    # Migration file (migrations/0001_create_users.py)
    from pykour.db.migrations import op

    def upgrade():
        op.create_table(
            "users",
            op.column("id", "INTEGER", primary_key=True, autoincrement=True),
            op.column("name", "VARCHAR(100)", nullable=False),
            op.column("email", "VARCHAR(255)", unique=True, nullable=False),
            op.column("active", "BOOLEAN", default=True),
        )
        op.create_index("idx_users_email", "users", ["email"], unique=True)

    def downgrade():
        op.drop_index("idx_users_email")
        op.drop_table("users")
"""

from pykour.db.migrations import op
from pykour.db.migrations.exceptions import (
    ArchiveBoundaryError,
    InvalidMigrationError,
    MigrationAlreadyAppliedError,
    MigrationError,
    MigrationNotAppliedError,
    MigrationNotFoundError,
    OperationError,
    SchemaIntrospectionError,
    SquashError,
    SquashRangeError,
)
from pykour.db.migrations.operations import (
    AddColumn,
    AlterColumn,
    CreateIndex,
    CreateTable,
    DropColumn,
    DropIndex,
    DropTable,
    ExecuteSQL,
    Operation,
    RenameColumn,
    RenameTable,
)
from pykour.db.migrations.table import (
    Column,
    ColumnDef,
    ColumnInfo,
    IndexDef,
    Table,
    TableInfo,
)
from pykour.db.migrations.types import (
    BigInt,
    Binary,
    Boolean,
    ColumnType,
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
from pykour.db.migrations.runner import Migration, MigrationRunner
from pykour.db.migrations.generator import MigrationGenerator
from pykour.db.migrations.differ import SchemaDiff, SchemaDiffer
from pykour.db.migrations.introspector import (
    SchemaIntrospector,
    SQLiteIntrospector,
    PostgreSQLIntrospector,
    MySQLIntrospector,
    get_introspector,
)
from pykour.db.migrations.squasher import MigrationSquasher, SquashResult
from pykour.db.migrations.analyzer import MigrationAnalyzer
from pykour.db.migrations.optimizer import OperationOptimizer
from pykour.db.migrations.presets import (
    ColumnGroup,
    timestamps,
    created,
    updated,
    audit,
    soft_delete,
)

__all__ = [
    # op module
    "op",
    # Types
    "ColumnType",
    "Integer",
    "SmallInt",
    "BigInt",
    "String",
    "Text",
    "Boolean",
    "Float",
    "Decimal",
    "DateTime",
    "Date",
    "Time",
    "Binary",
    "JSON",
    "UUID",
    # Table/Column
    "Table",
    "Column",
    "ColumnDef",
    "ColumnInfo",
    "IndexDef",
    "TableInfo",
    # Operations
    "Operation",
    "CreateTable",
    "DropTable",
    "AddColumn",
    "DropColumn",
    "AlterColumn",
    "RenameTable",
    "RenameColumn",
    "CreateIndex",
    "DropIndex",
    "ExecuteSQL",
    # Exceptions
    "MigrationError",
    "MigrationNotFoundError",
    "MigrationAlreadyAppliedError",
    "MigrationNotAppliedError",
    "InvalidMigrationError",
    "OperationError",
    "SchemaIntrospectionError",
    "SquashError",
    "SquashRangeError",
    "ArchiveBoundaryError",
    # Runner
    "Migration",
    "MigrationRunner",
    # Generator
    "MigrationGenerator",
    # Differ
    "SchemaDiff",
    "SchemaDiffer",
    # Introspector
    "SchemaIntrospector",
    "SQLiteIntrospector",
    "PostgreSQLIntrospector",
    "MySQLIntrospector",
    "get_introspector",
    # Squash
    "MigrationSquasher",
    "SquashResult",
    "MigrationAnalyzer",
    "OperationOptimizer",
    # Presets
    "ColumnGroup",
    "timestamps",
    "created",
    "updated",
    "audit",
    "soft_delete",
]
