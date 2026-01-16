"""Table and Column definitions for migrations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pykour.db.migrations.types import ColumnType

if TYPE_CHECKING:
    from pykour.db.access_policy.policy import AccessPolicy


@dataclass
class Column:
    """Column definition for table schema."""

    type: ColumnType
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False
    default: Any = None
    autoincrement: bool = False
    name: str = ""

    def to_sql(self, driver: str) -> str:
        """Generate SQL column definition."""
        parts = [self.name, self.type.to_sql(driver)]

        if self.primary_key:
            parts.append("PRIMARY KEY")
            if self.autoincrement:
                if driver == "sqlite":
                    parts.append("AUTOINCREMENT")
                elif driver == "postgresql":
                    pass
                elif driver == "mysql":
                    parts.append("AUTO_INCREMENT")
        elif not self.nullable:
            parts.append("NOT NULL")

        if self.unique and not self.primary_key:
            parts.append("UNIQUE")

        if self.default is not None and not self.autoincrement:
            if isinstance(self.default, bool):
                parts.append(f"DEFAULT {1 if self.default else 0}")
            elif isinstance(self.default, str):
                if self.default.lower() in ("now()", "current_timestamp"):
                    parts.append("DEFAULT CURRENT_TIMESTAMP")
                else:
                    # Escape single quotes to prevent SQL injection
                    escaped = self.default.replace("'", "''")
                    parts.append(f"DEFAULT '{escaped}'")
            else:
                parts.append(f"DEFAULT {self.default}")

        return " ".join(parts)


@dataclass
class ColumnDef:
    """Column definition for op.column() helper."""

    name: str
    type_sql: str
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False
    default: Any = None
    autoincrement: bool = False

    def to_sql(self, driver: str) -> str:
        """Generate SQL column definition."""
        parts = [self.name, self.type_sql]

        if self.primary_key:
            parts.append("PRIMARY KEY")
            if self.autoincrement:
                if driver == "sqlite":
                    parts.append("AUTOINCREMENT")
                elif driver == "mysql":
                    parts.append("AUTO_INCREMENT")

        if not self.nullable and not self.primary_key:
            parts.append("NOT NULL")

        if self.unique and not self.primary_key:
            parts.append("UNIQUE")

        if self.default is not None and not self.autoincrement:
            if isinstance(self.default, bool):
                parts.append(f"DEFAULT {1 if self.default else 0}")
            elif isinstance(self.default, str):
                if self.default.lower() in ("now()", "current_timestamp"):
                    parts.append("DEFAULT CURRENT_TIMESTAMP")
                else:
                    # Escape single quotes to prevent SQL injection
                    escaped = self.default.replace("'", "''")
                    parts.append(f"DEFAULT '{escaped}'")
            else:
                parts.append(f"DEFAULT {self.default}")

        return " ".join(parts)


@dataclass
class Index:
    """Index definition for table schema.

    Used to define indexes within Table class definitions.

    Example:
        class UserTable(Table):
            __tablename__ = "users"
            id = Column(Integer(), primary_key=True)
            email = Column(String(255))

            idx_email = Index(["email"], unique=True)
            idx_active = Index(["email"], where="active = 1")  # Partial index
    """

    columns: list[str]
    unique: bool = False
    where: str | None = None
    name: str = ""


@dataclass
class IndexDef:
    """Index definition (from introspection or op.create_index)."""

    name: str
    table: str
    columns: list[str]
    unique: bool = False
    where: str | None = None


@dataclass
class TableInfo:
    """Information about a database table (from introspection)."""

    name: str
    columns: list[ColumnInfo] = field(default_factory=list)
    indexes: list[IndexDef] = field(default_factory=list)
    primary_key: list[str] = field(default_factory=list)


@dataclass
class ColumnInfo:
    """Information about a database column (from introspection)."""

    name: str
    type: str
    nullable: bool = True
    default: Any = None
    autoincrement: bool = False
    primary_key: bool = False


class TableMeta(type):
    """Metaclass for Table to collect column, index, and access policy definitions."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
    ) -> TableMeta:
        columns: dict[str, Column] = {}
        indexes: dict[str, Index] = {}
        access_policy: "AccessPolicy | None" = None

        for key, value in namespace.items():
            if isinstance(value, Column):
                value.name = key
                columns[key] = value
            elif isinstance(value, Index):
                value.name = key
                indexes[key] = value

        # Check for __access_policy__ attribute
        if "__access_policy__" in namespace:
            access_policy = namespace["__access_policy__"]

        namespace["_columns"] = columns
        namespace["_indexes"] = indexes
        namespace["_access_policy"] = access_policy
        return super().__new__(mcs, name, bases, namespace)


class Table(metaclass=TableMeta):
    """Base class for table definitions.

    Example:
        class UserTable(Table):
            __tablename__ = "users"

            id = Column(Integer, primary_key=True, autoincrement=True)
            name = Column(String(100), nullable=False)
            email = Column(String(255), unique=True, nullable=False)

            idx_email = Index(["email"], unique=True)

    With AccessPolicy:
        from pykour.db.access_policy import AccessPolicy

        class OrderTable(Table):
            __tablename__ = "orders"
            __access_policy__ = AccessPolicy(
                name="orders_policy",
                select=["tenant_id = :tenant_id"],
                insert=["tenant_id = :tenant_id"],
                auto_set={"tenant_id": ":tenant_id"},
            )

            id = Column(Integer, primary_key=True, autoincrement=True)
            tenant_id = Column(String(36), nullable=False)
    """

    __tablename__: str
    __access_policy__: "AccessPolicy | None" = None
    _columns: dict[str, Column]
    _indexes: dict[str, Index]
    _access_policy: "AccessPolicy | None"

    @classmethod
    def get_tablename(cls) -> str:
        """Get the table name."""
        return getattr(cls, "__tablename__", cls.__name__.lower())

    @classmethod
    def get_columns(cls) -> dict[str, Column]:
        """Get all column definitions."""
        return cls._columns.copy()

    @classmethod
    def get_column(cls, name: str) -> Column | None:
        """Get a column by name."""
        return cls._columns.get(name)

    @classmethod
    def get_indexes(cls) -> dict[str, Index]:
        """Get all index definitions."""
        return cls._indexes.copy()

    @classmethod
    def get_index(cls, name: str) -> Index | None:
        """Get an index by name."""
        return cls._indexes.get(name)

    @classmethod
    def get_access_policy(cls) -> "AccessPolicy | None":
        """Get the access policy for this table."""
        return cls._access_policy
