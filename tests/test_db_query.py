"""Tests for query builders."""

import pytest

from pykour.db.query import DeleteQuery, InsertQuery, SelectQuery, UpdateQuery


# Mock executor functions for testing SQL generation
async def mock_execute(sql: str, args: tuple) -> int:
    return 0


async def mock_fetch_all(sql: str, args: tuple) -> list:
    return []


async def mock_fetch_one(sql: str, args: tuple):
    return None


class TestSelectQuery:
    """Tests for SelectQuery builder."""

    def test_simple_select(self) -> None:
        """SELECT * should work."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users")
        sql = query._build_sql()
        assert sql == "SELECT * FROM users"

    def test_select_columns(self) -> None:
        """SELECT with specific columns."""
        query = SelectQuery(
            ("id", "name"), mock_execute, mock_fetch_all, mock_fetch_one
        )
        query.from_("users")
        sql = query._build_sql()
        assert sql == "SELECT id, name FROM users"

    def test_where_clause(self) -> None:
        """WHERE clause should generate placeholders."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where(active=True, age=25)
        sql = query._build_sql()
        assert "WHERE" in sql
        assert "$1" in sql
        assert "$2" in sql

    def test_where_null(self) -> None:
        """WHERE with None should use IS NULL."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where(deleted_at=None)
        sql = query._build_sql()
        assert "deleted_at IS NULL" in sql

    def test_order_by(self) -> None:
        """ORDER BY clause."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").order_by("name")
        sql = query._build_sql()
        assert "ORDER BY name ASC" in sql

    def test_order_by_desc(self) -> None:
        """ORDER BY DESC."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").order_by("created_at", desc=True)
        sql = query._build_sql()
        assert "ORDER BY created_at DESC" in sql

    def test_limit_offset(self) -> None:
        """LIMIT and OFFSET."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").limit(10).offset(20)
        sql = query._build_sql()
        assert "LIMIT 10" in sql
        assert "OFFSET 20" in sql

    def test_join(self) -> None:
        """JOIN clause."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").join("orders", "users.id = orders.user_id")
        sql = query._build_sql()
        assert "INNER JOIN orders ON users.id = orders.user_id" in sql

    def test_left_join(self) -> None:
        """LEFT JOIN clause."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").left_join("profiles", "users.id = profiles.user_id")
        sql = query._build_sql()
        assert "LEFT JOIN profiles ON users.id = profiles.user_id" in sql

    def test_group_by(self) -> None:
        """GROUP BY clause."""
        query = SelectQuery(
            ("status", "COUNT(*)"), mock_execute, mock_fetch_all, mock_fetch_one
        )
        query.from_("orders").group_by("status")
        sql = query._build_sql()
        assert "GROUP BY status" in sql

    def test_chaining(self) -> None:
        """Method chaining should work."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        result = query.from_("users").where(active=True).order_by("name").limit(10)
        assert result is query

    def test_distinct(self) -> None:
        """SELECT DISTINCT."""
        query = SelectQuery(("name",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").distinct()
        sql = query._build_sql()
        assert sql == "SELECT DISTINCT name FROM users"

    def test_where_gt(self) -> None:
        """WHERE column > value."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_gt("age", 18)
        sql = query._build_sql()
        assert "WHERE age > $1" in sql

    def test_where_gte(self) -> None:
        """WHERE column >= value."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_gte("age", 21)
        sql = query._build_sql()
        assert "WHERE age >= $1" in sql

    def test_where_lt(self) -> None:
        """WHERE column < value."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_lt("age", 65)
        sql = query._build_sql()
        assert "WHERE age < $1" in sql

    def test_where_lte(self) -> None:
        """WHERE column <= value."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_lte("score", 100)
        sql = query._build_sql()
        assert "WHERE score <= $1" in sql

    def test_where_in(self) -> None:
        """WHERE column IN (...)."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_in("status", ["active", "pending"])
        sql = query._build_sql()
        assert "WHERE status IN ($1, $2)" in sql

    def test_where_in_empty(self) -> None:
        """WHERE column IN () with empty list."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_in("status", [])
        sql = query._build_sql()
        assert "WHERE 1 = 0" in sql  # Always false for empty IN

    def test_where_not_in(self) -> None:
        """WHERE column NOT IN (...)."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_not_in("role", ["admin", "superuser"])
        sql = query._build_sql()
        assert "WHERE role NOT IN ($1, $2)" in sql

    def test_where_not_in_empty(self) -> None:
        """WHERE column NOT IN () with empty list."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_not_in("role", [])
        sql = query._build_sql()
        assert "WHERE 1 = 1" in sql  # Always true for empty NOT IN

    def test_where_between(self) -> None:
        """WHERE column BETWEEN min AND max."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("products").where_between("price", 100, 500)
        sql = query._build_sql()
        assert "WHERE price BETWEEN $1 AND $2" in sql

    def test_where_like(self) -> None:
        """WHERE column LIKE pattern."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_like("name", "John%")
        sql = query._build_sql()
        assert "WHERE name LIKE $1" in sql

    def test_where_is_null(self) -> None:
        """WHERE column IS NULL."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_is_null("deleted_at")
        sql = query._build_sql()
        assert "WHERE deleted_at IS NULL" in sql

    def test_where_is_not_null(self) -> None:
        """WHERE column IS NOT NULL."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users").where_is_not_null("email")
        sql = query._build_sql()
        assert "WHERE email IS NOT NULL" in sql

    def test_combined_conditions(self) -> None:
        """Multiple WHERE conditions combined with AND."""
        query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("products").where(active=True).where_gte("price", 100).where_lte(
            "price", 500
        )
        sql = query._build_sql()
        assert "WHERE active = $1 AND price >= $2 AND price <= $3" in sql


class TestInsertQuery:
    """Tests for InsertQuery builder."""

    def test_insert_values(self) -> None:
        """INSERT with values."""
        query = InsertQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.values(name="Alice", age=30)
        sql = query._build_sql()
        assert "INSERT INTO users" in sql
        assert "name" in sql
        assert "age" in sql
        assert "$1" in sql
        assert "$2" in sql

    def test_insert_returning(self) -> None:
        """INSERT with RETURNING."""
        query = InsertQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.values(name="Alice").returning("id")
        sql = query._build_sql()
        assert "RETURNING id" in sql

    def test_insert_many(self) -> None:
        """INSERT multiple rows."""
        query = InsertQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.values_many([{"name": "Alice"}, {"name": "Bob"}])
        sql = query._build_sql()
        # Should have two value sets
        assert sql.count("(") >= 2

    def test_on_conflict_do_nothing(self) -> None:
        """ON CONFLICT DO NOTHING."""
        query = InsertQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.values(name="Alice").on_conflict_do_nothing()
        sql = query._build_sql()
        assert "ON CONFLICT DO NOTHING" in sql

    def test_insert_no_values_raises(self) -> None:
        """INSERT without values should raise."""
        query = InsertQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        with pytest.raises(ValueError, match="No values"):
            query._build_sql()


class TestUpdateQuery:
    """Tests for UpdateQuery builder."""

    def test_update_set(self) -> None:
        """UPDATE with SET."""
        query = UpdateQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.set(name="Bob", age=25)
        sql = query._build_sql()
        assert "UPDATE users SET" in sql
        assert "$1" in sql

    def test_update_where(self) -> None:
        """UPDATE with WHERE."""
        query = UpdateQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.set(name="Bob").where(id=1)
        sql = query._build_sql()
        assert "WHERE" in sql

    def test_update_returning(self) -> None:
        """UPDATE with RETURNING."""
        query = UpdateQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.set(name="Bob").where(id=1).returning("id", "name")
        sql = query._build_sql()
        assert "RETURNING id, name" in sql

    def test_update_no_set_raises(self) -> None:
        """UPDATE without SET should raise."""
        query = UpdateQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        with pytest.raises(ValueError, match="No columns"):
            query._build_sql()

    def test_update_where_gt(self) -> None:
        """UPDATE with WHERE column > value."""
        query = UpdateQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.set(status="expired").where_lt("last_login", "2024-01-01")
        sql = query._build_sql()
        assert "WHERE last_login < $2" in sql

    def test_update_where_in(self) -> None:
        """UPDATE with WHERE column IN (...)."""
        query = UpdateQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.set(active=False).where_in("status", ["pending", "inactive"])
        sql = query._build_sql()
        assert "WHERE status IN ($2, $3)" in sql


class TestDeleteQuery:
    """Tests for DeleteQuery builder."""

    def test_delete(self) -> None:
        """DELETE without WHERE."""
        query = DeleteQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        sql = query._build_sql()
        assert sql == "DELETE FROM users"

    def test_delete_where(self) -> None:
        """DELETE with WHERE."""
        query = DeleteQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.where(id=1)
        sql = query._build_sql()
        assert "WHERE" in sql
        assert "$1" in sql

    def test_delete_returning(self) -> None:
        """DELETE with RETURNING."""
        query = DeleteQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.where(id=1).returning("id")
        sql = query._build_sql()
        assert "RETURNING id" in sql

    def test_delete_where_lt(self) -> None:
        """DELETE with WHERE column < value."""
        query = DeleteQuery("logs", mock_execute, mock_fetch_all, mock_fetch_one)
        query.where_lt("created_at", "2024-01-01")
        sql = query._build_sql()
        assert "WHERE created_at < $1" in sql

    def test_delete_where_between(self) -> None:
        """DELETE with WHERE BETWEEN."""
        query = DeleteQuery("temp_data", mock_execute, mock_fetch_all, mock_fetch_one)
        query.where_between("timestamp", "2024-01-01", "2024-02-01")
        sql = query._build_sql()
        assert "WHERE timestamp BETWEEN $1 AND $2" in sql

    def test_delete_where_is_null(self) -> None:
        """DELETE with WHERE IS NULL."""
        query = DeleteQuery("users", mock_execute, mock_fetch_all, mock_fetch_one)
        query.where_is_null("verified_at")
        sql = query._build_sql()
        assert "WHERE verified_at IS NULL" in sql


class TestFetchVal:
    """Tests for BaseQuery.fetch_val() shared implementation."""

    @pytest.mark.asyncio
    async def test_select_fetch_val_returns_first_column(self) -> None:
        """fetch_val returns the first column value from SelectQuery."""
        from pykour.db.result import Row

        async def fetch_one_row(sql: str, args: tuple):
            return Row({"count": 42, "name": "Alice"})

        query = SelectQuery(("count(*)",), mock_execute, mock_fetch_all, fetch_one_row)
        query.from_("users")
        val = await query.fetch_val()
        assert val == 42

    @pytest.mark.asyncio
    async def test_select_fetch_val_returns_none_when_no_row(self) -> None:
        """fetch_val returns None when no row is found."""
        query = SelectQuery(("count(*)",), mock_execute, mock_fetch_all, mock_fetch_one)
        query.from_("users")
        val = await query.fetch_val()
        assert val is None

    @pytest.mark.asyncio
    async def test_insert_fetch_val_returns_first_column(self) -> None:
        """fetch_val returns the first column value from InsertQuery."""
        from pykour.db.result import Row

        async def fetch_one_row(sql: str, args: tuple):
            return Row({"id": 99})

        query = InsertQuery("users", mock_execute, mock_fetch_all, fetch_one_row)
        query.values(name="Alice").returning("id")
        val = await query.fetch_val()
        assert val == 99

    @pytest.mark.asyncio
    async def test_fetch_val_empty_row_returns_none(self) -> None:
        """fetch_val returns None when the row has no values."""
        from pykour.db.result import Row

        async def fetch_one_empty(sql: str, args: tuple):
            return Row()

        query = SelectQuery(("*",), mock_execute, mock_fetch_all, fetch_one_empty)
        query.from_("users")
        val = await query.fetch_val()
        assert val is None


@pytest.mark.parametrize(
    "columns,expected",
    [
        (("*",), "SELECT * FROM users"),
        (("id",), "SELECT id FROM users"),
        (("id", "name", "email"), "SELECT id, name, email FROM users"),
    ],
)
def test_select_columns_parametrize(columns: tuple, expected: str) -> None:
    """Parametrized test for SELECT columns."""
    query = SelectQuery(columns, mock_execute, mock_fetch_all, mock_fetch_one)
    query.from_("users")
    assert query._build_sql() == expected


@pytest.mark.parametrize(
    "method,column,value,expected_op",
    [
        ("where_gt", "age", 18, ">"),
        ("where_gte", "age", 18, ">="),
        ("where_lt", "age", 65, "<"),
        ("where_lte", "age", 65, "<="),
        ("where_like", "name", "Al%", "LIKE"),
    ],
)
def test_where_clause_mixin_operators_parametrize(
    method: str, column: str, value: object, expected_op: str
) -> None:
    """Parametrized test for WhereClauseMixin comparison operators."""
    query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
    query.from_("users")
    getattr(query, method)(column, value)
    sql = query._build_sql()
    assert f"WHERE {column} {expected_op} $1" in sql


def test_where_raw_out_of_order_placeholders() -> None:
    """where_raw handles out-of-order $N placeholders correctly."""
    query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
    query.from_("t").where_raw("$2 > $1", 10, 20)
    sql = query._build_sql()
    assert "WHERE" in sql
    assert query._params == [10, 20]


def test_where_raw_repeated_placeholder() -> None:
    """where_raw handles repeated $N placeholders."""
    query = SelectQuery(("*",), mock_execute, mock_fetch_all, mock_fetch_one)
    query.from_("t").where_raw("x BETWEEN $1 AND $1", 5)
    sql = query._build_sql()
    assert "WHERE" in sql
    # Only one unique param added since $1 is repeated
    assert len(query._params) == 1
