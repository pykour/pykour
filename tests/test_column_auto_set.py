"""Tests for Column auto_set functionality."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


from pykour.db.access_policy.context import set_policy_context, clear_policy_context
from pykour.db.access_policy.resolver import ValueResolver, _utc_now_naive
from pykour.db.migrations import Column, Table
from pykour.db.migrations.types import DateTime, Integer, String
from pykour.db.query import InsertQuery, UpdateQuery


# Test Table definitions
class ItemTable(Table):
    """Table with auto_now and auto_now_add columns."""

    __tablename__ = "items"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(100))
    created_at = Column(DateTime(), auto_now_add=True)
    updated_at = Column(DateTime(), auto_now=True)


class AuditTable(Table):
    """Table with context-based auto_set columns."""

    __tablename__ = "audits"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    data = Column(String(255))
    created_by = Column(String(36), auto_set_on_insert=":user_id")
    updated_by = Column(String(36), auto_set=":user_id")
    tenant_id = Column(String(36), auto_set=":tenant_id")


class MixedTable(Table):
    """Table with both timestamp and context auto_set columns."""

    __tablename__ = "mixed"

    id = Column(Integer(), primary_key=True, autoincrement=True)
    name = Column(String(100))
    created_at = Column(DateTime(), auto_now_add=True)
    updated_at = Column(DateTime(), auto_now=True)
    created_by = Column(String(36), auto_set_on_insert=":user_id")
    updated_by = Column(String(36), auto_set=":user_id")


# Mock executor functions for testing SQL generation
async def mock_execute(sql: str, args: tuple[Any, ...]) -> int:
    return 0


async def mock_fetch_all(sql: str, args: tuple[Any, ...]) -> list[Any]:
    return []


async def mock_fetch_one(sql: str, args: tuple[Any, ...]) -> Any:
    return None


class TestColumnAutoSetOptions:
    """Test Column dataclass auto_set options."""

    def test_auto_now_add_default(self) -> None:
        """auto_now_add should default to False."""
        col = Column(DateTime())
        assert col.auto_now_add is False

    def test_auto_now_default(self) -> None:
        """auto_now should default to False."""
        col = Column(DateTime())
        assert col.auto_now is False

    def test_auto_set_on_insert_default(self) -> None:
        """auto_set_on_insert should default to None."""
        col = Column(String(36))
        assert col.auto_set_on_insert is None

    def test_auto_set_default(self) -> None:
        """auto_set should default to None."""
        col = Column(String(36))
        assert col.auto_set is None

    def test_auto_now_add_option(self) -> None:
        """auto_now_add should be settable."""
        col = Column(DateTime(), auto_now_add=True)
        assert col.auto_now_add is True

    def test_auto_now_option(self) -> None:
        """auto_now should be settable."""
        col = Column(DateTime(), auto_now=True)
        assert col.auto_now is True

    def test_auto_set_on_insert_option(self) -> None:
        """auto_set_on_insert should be settable."""
        col = Column(String(36), auto_set_on_insert=":user_id")
        assert col.auto_set_on_insert == ":user_id"

    def test_auto_set_option(self) -> None:
        """auto_set should be settable."""
        col = Column(String(36), auto_set=":tenant_id")
        assert col.auto_set == ":tenant_id"


class TestTableGetAutoSetColumns:
    """Test Table.get_auto_set_columns() method."""

    def test_get_auto_set_columns_for_insert(self) -> None:
        """Should return columns with auto_now_add, auto_now, auto_set_on_insert, auto_set."""
        columns = ItemTable.get_auto_set_columns(on_insert=True)
        assert "created_at" in columns
        assert "updated_at" in columns
        assert "id" not in columns
        assert "name" not in columns

    def test_get_auto_set_columns_for_update(self) -> None:
        """Should return only columns with auto_now and auto_set."""
        columns = ItemTable.get_auto_set_columns(on_insert=False)
        assert "updated_at" in columns
        assert "created_at" not in columns  # auto_now_add only for INSERT

    def test_get_auto_set_columns_with_context(self) -> None:
        """Should return columns with auto_set options."""
        columns = AuditTable.get_auto_set_columns(on_insert=True)
        assert "created_by" in columns
        assert "updated_by" in columns
        assert "tenant_id" in columns

    def test_get_auto_set_columns_for_update_with_context(self) -> None:
        """Should return only auto_set columns for UPDATE."""
        columns = AuditTable.get_auto_set_columns(on_insert=False)
        assert "updated_by" in columns
        assert "tenant_id" in columns
        assert "created_by" not in columns  # auto_set_on_insert only for INSERT


class TestValueResolver:
    """Test ValueResolver class."""

    def test_resolve_literal(self) -> None:
        """Should return literal value as-is."""
        resolver = ValueResolver()
        assert resolver.resolve("some_value") == "some_value"

    def test_resolve_now(self) -> None:
        """Should return current UTC datetime (naive) for :now."""
        resolver = ValueResolver()
        before = _utc_now_naive()
        result = resolver.resolve(":now")
        after = _utc_now_naive()

        assert isinstance(result, datetime)
        assert result.tzinfo is None  # Should be naive
        assert before <= result <= after

    def test_resolve_user_id_from_context(self) -> None:
        """Should resolve :user_id from policy context."""
        set_policy_context(user_id="user-123")
        try:
            from pykour.db.access_policy.context import get_policy_context

            context = get_policy_context()
            resolver = ValueResolver(context)
            assert resolver.resolve(":user_id") == "user-123"
        finally:
            clear_policy_context()

    def test_resolve_tenant_id_from_context(self) -> None:
        """Should resolve :tenant_id from policy context."""
        set_policy_context(tenant_id="tenant-456")
        try:
            from pykour.db.access_policy.context import get_policy_context

            context = get_policy_context()
            resolver = ValueResolver(context)
            assert resolver.resolve(":tenant_id") == "tenant-456"
        finally:
            clear_policy_context()

    def test_resolve_custom_from_context(self) -> None:
        """Should resolve custom keys from policy context."""
        set_policy_context(custom_key="custom-value")
        try:
            from pykour.db.access_policy.context import get_policy_context

            context = get_policy_context()
            resolver = ValueResolver(context)
            assert resolver.resolve(":custom_key") == "custom-value"
        finally:
            clear_policy_context()

    def test_resolve_without_context(self) -> None:
        """Should return None for context values without context."""
        resolver = ValueResolver(None)
        assert resolver.resolve(":user_id") is None

    def test_resolve_for_insert_auto_now_add(self) -> None:
        """Should return naive datetime for auto_now_add=True."""
        resolver = ValueResolver()
        before = _utc_now_naive()
        result = resolver.resolve_for_insert(
            auto_now_add=True, auto_now=False, auto_set_on_insert=None, auto_set=None
        )
        after = _utc_now_naive()

        assert isinstance(result, datetime)
        assert result.tzinfo is None  # Should be naive
        assert before <= result <= after

    def test_resolve_for_insert_auto_now(self) -> None:
        """Should return naive datetime for auto_now=True on INSERT."""
        resolver = ValueResolver()
        before = _utc_now_naive()
        result = resolver.resolve_for_insert(
            auto_now_add=False, auto_now=True, auto_set_on_insert=None, auto_set=None
        )
        after = _utc_now_naive()

        assert isinstance(result, datetime)
        assert result.tzinfo is None  # Should be naive
        assert before <= result <= after

    def test_resolve_for_insert_auto_set_on_insert(self) -> None:
        """Should resolve auto_set_on_insert value."""
        set_policy_context(user_id="user-789")
        try:
            from pykour.db.access_policy.context import get_policy_context

            context = get_policy_context()
            resolver = ValueResolver(context)
            result = resolver.resolve_for_insert(
                auto_now_add=False,
                auto_now=False,
                auto_set_on_insert=":user_id",
                auto_set=None,
            )
            assert result == "user-789"
        finally:
            clear_policy_context()

    def test_resolve_for_update_auto_now(self) -> None:
        """Should return naive datetime for auto_now=True on UPDATE."""
        resolver = ValueResolver()
        before = _utc_now_naive()
        result = resolver.resolve_for_update(auto_now=True, auto_set=None)
        after = _utc_now_naive()

        assert isinstance(result, datetime)
        assert result.tzinfo is None  # Should be naive
        assert before <= result <= after

    def test_resolve_for_update_auto_set(self) -> None:
        """Should resolve auto_set value on UPDATE."""
        set_policy_context(user_id="user-update")
        try:
            from pykour.db.access_policy.context import get_policy_context

            context = get_policy_context()
            resolver = ValueResolver(context)
            result = resolver.resolve_for_update(auto_now=False, auto_set=":user_id")
            assert result == "user-update"
        finally:
            clear_policy_context()


class TestInsertQueryAutoSet:
    """Test InsertQuery with column auto_set."""

    def test_insert_with_auto_now_add(self) -> None:
        """INSERT should include auto_now_add columns."""
        query = InsertQuery(
            "items",
            mock_execute,
            mock_fetch_all,
            mock_fetch_one,
            table_classes={"items": ItemTable},
        )
        query.values(name="Test Item")

        # Access the internal method to check values
        values = query._apply_column_auto_set([{"name": "Test Item"}])

        assert len(values) == 1
        assert "name" in values[0]
        assert "created_at" in values[0]
        assert "updated_at" in values[0]
        assert isinstance(values[0]["created_at"], datetime)
        assert isinstance(values[0]["updated_at"], datetime)

    def test_insert_user_provided_value_not_overwritten(self) -> None:
        """User-provided values should not be overwritten by auto_set."""
        query = InsertQuery(
            "items",
            mock_execute,
            mock_fetch_all,
            mock_fetch_one,
            table_classes={"items": ItemTable},
        )
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        query.values(name="Test Item", created_at=custom_time)

        values = query._apply_column_auto_set(
            [{"name": "Test Item", "created_at": custom_time}]
        )

        assert values[0]["created_at"] == custom_time  # Not overwritten

    def test_insert_with_context_auto_set(self) -> None:
        """INSERT should include context-based auto_set columns."""
        set_policy_context(user_id="user-insert", tenant_id="tenant-insert")
        try:
            from pykour.db.access_policy.context import get_policy_context

            query = InsertQuery(
                "audits",
                mock_execute,
                mock_fetch_all,
                mock_fetch_one,
                table_classes={"audits": AuditTable},
                get_policy_context=get_policy_context,
            )
            query.values(data="Test data")

            values = query._apply_column_auto_set([{"data": "Test data"}])

            assert values[0]["created_by"] == "user-insert"
            assert values[0]["updated_by"] == "user-insert"
            assert values[0]["tenant_id"] == "tenant-insert"
        finally:
            clear_policy_context()

    def test_insert_without_table_class(self) -> None:
        """INSERT without registered table class should work without auto_set."""
        query = InsertQuery(
            "unknown_table",
            mock_execute,
            mock_fetch_all,
            mock_fetch_one,
            table_classes={},
        )
        query.values(name="Test")

        values = query._apply_column_auto_set([{"name": "Test"}])

        assert values == [{"name": "Test"}]


class TestUpdateQueryAutoSet:
    """Test UpdateQuery with column auto_set."""

    def test_update_with_auto_now(self) -> None:
        """UPDATE should include auto_now columns."""
        query = UpdateQuery(
            "items",
            mock_execute,
            mock_fetch_all,
            mock_fetch_one,
            table_classes={"items": ItemTable},
        )
        query.set(name="Updated Item")

        # Build SQL to trigger auto_set
        sql = query._build_sql()

        assert "updated_at = $2" in sql  # $1 is name, $2 is auto_now
        assert len(query._params) == 2
        assert isinstance(query._params[1], datetime)

    def test_update_auto_now_not_overwrite_user_value(self) -> None:
        """User-provided updated_at should not be overwritten."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        query = UpdateQuery(
            "items",
            mock_execute,
            mock_fetch_all,
            mock_fetch_one,
            table_classes={"items": ItemTable},
        )
        query.set(name="Updated Item", updated_at=custom_time)

        sql = query._build_sql()

        # Should only have user-provided columns, no additional auto_set
        assert sql.count("updated_at") == 1
        assert query._params[1] == custom_time

    def test_update_with_context_auto_set(self) -> None:
        """UPDATE should include context-based auto_set columns."""
        set_policy_context(user_id="user-update", tenant_id="tenant-update")
        try:
            from pykour.db.access_policy.context import get_policy_context

            query = UpdateQuery(
                "audits",
                mock_execute,
                mock_fetch_all,
                mock_fetch_one,
                table_classes={"audits": AuditTable},
                get_policy_context=get_policy_context,
            )
            query.set(data="Updated data")

            sql = query._build_sql()

            # Should have data, updated_by, and tenant_id
            assert "data = $1" in sql
            assert "updated_by = $2" in sql
            assert "tenant_id = $3" in sql
            assert query._params[1] == "user-update"
            assert query._params[2] == "tenant-update"
        finally:
            clear_policy_context()

    def test_update_without_table_class(self) -> None:
        """UPDATE without registered table class should work without auto_set."""
        query = UpdateQuery(
            "unknown_table",
            mock_execute,
            mock_fetch_all,
            mock_fetch_one,
            table_classes={},
        )
        query.set(name="Updated")

        sql = query._build_sql()

        assert sql == "UPDATE unknown_table SET name = $1"


class TestMixedAutoSet:
    """Test tables with both timestamp and context auto_set."""

    def test_insert_mixed_auto_set(self) -> None:
        """INSERT should handle both timestamp and context auto_set."""
        set_policy_context(user_id="user-mixed")
        try:
            from pykour.db.access_policy.context import get_policy_context

            query = InsertQuery(
                "mixed",
                mock_execute,
                mock_fetch_all,
                mock_fetch_one,
                table_classes={"mixed": MixedTable},
                get_policy_context=get_policy_context,
            )
            query.values(name="Mixed Item")

            values = query._apply_column_auto_set([{"name": "Mixed Item"}])

            assert "created_at" in values[0]
            assert "updated_at" in values[0]
            assert "created_by" in values[0]
            assert "updated_by" in values[0]
            assert isinstance(values[0]["created_at"], datetime)
            assert isinstance(values[0]["updated_at"], datetime)
            assert values[0]["created_by"] == "user-mixed"
            assert values[0]["updated_by"] == "user-mixed"
        finally:
            clear_policy_context()

    def test_update_mixed_auto_set(self) -> None:
        """UPDATE should handle both timestamp and context auto_set."""
        set_policy_context(user_id="user-mixed-update")
        try:
            from pykour.db.access_policy.context import get_policy_context

            query = UpdateQuery(
                "mixed",
                mock_execute,
                mock_fetch_all,
                mock_fetch_one,
                table_classes={"mixed": MixedTable},
                get_policy_context=get_policy_context,
            )
            query.set(name="Updated Mixed")

            sql = query._build_sql()

            # Should have name, updated_at, and updated_by
            assert "name = $1" in sql
            assert "updated_at" in sql
            assert "updated_by" in sql
            # created_at and created_by should NOT be in UPDATE
            assert "created_at" not in sql
            assert "created_by" not in sql
        finally:
            clear_policy_context()
