"""Access policy migration operations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pykour.db.migrations.operations import Operation
from pykour.db.sql_utils import validate_identifier, validate_rls_condition

if TYPE_CHECKING:
    from pykour.db.drivers.base import BaseDriver


@dataclass
class CreateAccessPolicy(Operation):
    """Create an access policy on a table.

    For PostgreSQL: Creates native RLS policies.
    For MySQL/SQLite: Stores policy metadata for application-level enforcement.

    Example:
        op.create_access_policy(
            "orders",
            "orders_tenant_policy",
            select=["tenant_id = :tenant_id"],
            insert=["tenant_id = :tenant_id"],
            update=["tenant_id = :tenant_id", "user_id = :user_id"],
            delete=["tenant_id = :tenant_id", "user_id = :user_id"],
            auto_set={"tenant_id": ":tenant_id"},
        )
    """

    table: str
    policy_name: str
    select: list[str] = field(default_factory=list)
    insert: list[str] = field(default_factory=list)
    update: list[str] = field(default_factory=list)
    delete: list[str] = field(default_factory=list)
    auto_set: dict[str, str] = field(default_factory=dict)
    bypass_roles: list[str] = field(default_factory=list)

    async def execute(self, driver: "BaseDriver", conn: Any) -> None:
        """Execute the operation."""
        # Validate table and policy names
        validate_identifier(self.table, "table")
        validate_identifier(self.policy_name, "policy")

        # Validate RLS conditions
        for condition in self.select + self.insert + self.update + self.delete:
            validate_rls_condition(condition)

        driver_name = driver.driver_name

        if driver_name == "postgresql":
            await self._execute_postgresql(driver, conn)
        else:
            # MySQL/SQLite: Store in metadata table
            await self._store_policy_metadata(driver, conn, driver_name)

    async def _execute_postgresql(self, driver: "BaseDriver", conn: Any) -> None:
        """Create native PostgreSQL RLS policies."""
        table = self.table

        # Enable RLS on table
        await driver.execute(
            conn,
            f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY",
            (),
        )

        # Create policies for each action
        action_map = [
            ("SELECT", self.select),
            ("INSERT", self.insert),
            ("UPDATE", self.update),
            ("DELETE", self.delete),
        ]

        for action, conditions in action_map:
            if conditions:
                condition = self._convert_to_pg_condition(conditions)
                policy_name = f"{self.policy_name}_{action.lower()}"

                if action == "INSERT":
                    # INSERT uses WITH CHECK instead of USING
                    sql = f"""
                        CREATE POLICY {policy_name} ON {table}
                        FOR {action}
                        WITH CHECK ({condition})
                    """
                else:
                    sql = f"""
                        CREATE POLICY {policy_name} ON {table}
                        FOR {action}
                        USING ({condition})
                    """
                await driver.execute(conn, sql, ())

    def _convert_to_pg_condition(self, conditions: list[str]) -> str:
        """Convert :param to current_setting('app.param').

        Args:
            conditions: List of condition strings with :param syntax.

        Returns:
            Combined condition with PostgreSQL current_setting() syntax.
        """
        combined = " AND ".join(f"({c})" for c in conditions)
        # Replace :tenant_id with current_setting('app.tenant_id')::text
        return re.sub(
            r":(\w+)",
            r"current_setting('app.\1', true)",
            combined,
        )

    async def _store_policy_metadata(
        self,
        driver: "BaseDriver",
        conn: Any,
        driver_name: str,
    ) -> None:
        """Store policy in _pykour_access_policies table."""
        # Ensure metadata table exists
        if driver_name == "sqlite":
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS _pykour_access_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    select_rules TEXT,
                    insert_rules TEXT,
                    update_rules TEXT,
                    delete_rules TEXT,
                    auto_set TEXT,
                    bypass_roles TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(table_name, policy_name)
                )
            """
        else:
            # MySQL
            create_table_sql = """
                CREATE TABLE IF NOT EXISTS _pykour_access_policies (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_name VARCHAR(255) NOT NULL,
                    policy_name VARCHAR(255) NOT NULL,
                    select_rules TEXT,
                    insert_rules TEXT,
                    update_rules TEXT,
                    delete_rules TEXT,
                    auto_set TEXT,
                    bypass_roles TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(table_name, policy_name)
                )
            """

        await driver.execute(conn, create_table_sql, ())

        # Insert policy
        insert_sql = driver.convert_placeholders(
            """
            INSERT INTO _pykour_access_policies
            (table_name, policy_name, select_rules, insert_rules,
             update_rules, delete_rules, auto_set, bypass_roles)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            8,
        )

        await driver.execute(
            conn,
            insert_sql,
            (
                self.table,
                self.policy_name,
                json.dumps(self.select),
                json.dumps(self.insert),
                json.dumps(self.update),
                json.dumps(self.delete),
                json.dumps(self.auto_set),
                json.dumps(self.bypass_roles),
            ),
        )

    def reverse(self) -> "Operation":
        """Return the reverse operation."""
        return DropAccessPolicy(
            self.table,
            self.policy_name,
            _policy_backup={
                "select": self.select,
                "insert": self.insert,
                "update": self.update,
                "delete": self.delete,
                "auto_set": self.auto_set,
                "bypass_roles": self.bypass_roles,
            },
        )

    def to_code(self) -> str:
        """Generate Python code for this operation."""
        parts = [f'"{self.table}"', f'"{self.policy_name}"']
        if self.select:
            parts.append(f"select={self.select!r}")
        if self.insert:
            parts.append(f"insert={self.insert!r}")
        if self.update:
            parts.append(f"update={self.update!r}")
        if self.delete:
            parts.append(f"delete={self.delete!r}")
        if self.auto_set:
            parts.append(f"auto_set={self.auto_set!r}")
        if self.bypass_roles:
            parts.append(f"bypass_roles={self.bypass_roles!r}")
        return f"op.create_access_policy({', '.join(parts)})"


@dataclass
class DropAccessPolicy(Operation):
    """Drop an access policy from a table.

    Example:
        op.drop_access_policy("orders", "orders_tenant_policy")
    """

    table: str
    policy_name: str
    _policy_backup: dict[str, Any] | None = None

    async def execute(self, driver: "BaseDriver", conn: Any) -> None:
        """Execute the operation."""
        validate_identifier(self.table, "table")
        validate_identifier(self.policy_name, "policy")

        driver_name = driver.driver_name

        if driver_name == "postgresql":
            await self._execute_postgresql(driver, conn)
        else:
            await self._remove_policy_metadata(driver, conn)

    async def _execute_postgresql(self, driver: "BaseDriver", conn: Any) -> None:
        """Drop PostgreSQL RLS policies."""
        for action in ["select", "insert", "update", "delete"]:
            policy_name = f"{self.policy_name}_{action}"
            await driver.execute(
                conn,
                f"DROP POLICY IF EXISTS {policy_name} ON {self.table}",
                (),
            )

        # Disable RLS (only if no other policies exist)
        # Note: This might fail if other policies exist, which is fine
        try:
            await driver.execute(
                conn,
                f"ALTER TABLE {self.table} DISABLE ROW LEVEL SECURITY",
                (),
            )
        except Exception:
            pass  # Other policies might still exist

    async def _remove_policy_metadata(
        self,
        driver: "BaseDriver",
        conn: Any,
    ) -> None:
        """Remove policy from _pykour_access_policies table."""
        delete_sql = driver.convert_placeholders(
            """
            DELETE FROM _pykour_access_policies
            WHERE table_name = $1 AND policy_name = $2
            """,
            2,
        )
        await driver.execute(conn, delete_sql, (self.table, self.policy_name))

    def reverse(self) -> "Operation":
        """Return the reverse operation."""
        if self._policy_backup is None:
            raise ValueError("Cannot reverse DropAccessPolicy without backup")
        return CreateAccessPolicy(
            self.table,
            self.policy_name,
            select=self._policy_backup.get("select", []),
            insert=self._policy_backup.get("insert", []),
            update=self._policy_backup.get("update", []),
            delete=self._policy_backup.get("delete", []),
            auto_set=self._policy_backup.get("auto_set", {}),
            bypass_roles=self._policy_backup.get("bypass_roles", []),
        )

    def to_code(self) -> str:
        """Generate Python code for this operation."""
        return f'op.drop_access_policy("{self.table}", "{self.policy_name}")'


@dataclass
class AlterAccessPolicy(Operation):
    """Alter an existing access policy.

    Example:
        op.alter_access_policy(
            "orders",
            "orders_tenant_policy",
            new_select=["tenant_id = :tenant_id", "active = true"],
        )
    """

    table: str
    policy_name: str
    new_select: list[str] | None = None
    new_insert: list[str] | None = None
    new_update: list[str] | None = None
    new_delete: list[str] | None = None
    new_auto_set: dict[str, str] | None = None
    new_bypass_roles: list[str] | None = None
    _old_policy: dict[str, Any] | None = None

    async def execute(self, driver: "BaseDriver", conn: Any) -> None:
        """Execute the operation by dropping and recreating the policy."""
        validate_identifier(self.table, "table")
        validate_identifier(self.policy_name, "policy")

        # Validate new RLS conditions
        new_conditions = []
        if self.new_select:
            new_conditions.extend(self.new_select)
        if self.new_insert:
            new_conditions.extend(self.new_insert)
        if self.new_update:
            new_conditions.extend(self.new_update)
        if self.new_delete:
            new_conditions.extend(self.new_delete)
        for condition in new_conditions:
            validate_rls_condition(condition)

        driver_name = driver.driver_name

        # First, get the current policy for backup (needed for reverse())
        if driver_name == "postgresql":
            self._old_policy = await self._get_current_policy_postgresql(driver, conn)
        else:
            self._old_policy = await self._get_current_policy(driver, conn)

        # Drop the old policy
        drop_op = DropAccessPolicy(self.table, self.policy_name)
        await drop_op.execute(driver, conn)

        # Create new policy with merged settings
        old = self._old_policy or {}
        create_op = CreateAccessPolicy(
            self.table,
            self.policy_name,
            select=self.new_select
            if self.new_select is not None
            else old.get("select", []),
            insert=self.new_insert
            if self.new_insert is not None
            else old.get("insert", []),
            update=self.new_update
            if self.new_update is not None
            else old.get("update", []),
            delete=self.new_delete
            if self.new_delete is not None
            else old.get("delete", []),
            auto_set=self.new_auto_set
            if self.new_auto_set is not None
            else old.get("auto_set", {}),
            bypass_roles=self.new_bypass_roles
            if self.new_bypass_roles is not None
            else old.get("bypass_roles", []),
        )
        await create_op.execute(driver, conn)

    async def _get_current_policy_postgresql(
        self,
        driver: "BaseDriver",
        conn: Any,
    ) -> dict[str, Any]:
        """Get current policy from PostgreSQL pg_policies view.

        Queries the system catalog to extract USING and WITH CHECK expressions
        for each action type (SELECT, INSERT, UPDATE, DELETE).
        """
        # Query pg_policies for all policies matching our naming pattern
        # Policies are named as {policy_name}_{action} (e.g., my_policy_select)
        select_sql = """
            SELECT policyname, qual, with_check
            FROM pg_policies
            WHERE tablename = $1
              AND policyname LIKE $2
        """
        pattern = f"{self.policy_name}_%"
        rows = await driver.fetch_all(conn, select_sql, (self.table, pattern))

        if not rows:
            return {}

        result: dict[str, Any] = {
            "select": [],
            "insert": [],
            "update": [],
            "delete": [],
            "auto_set": {},
            "bypass_roles": [],
        }

        for row in rows:
            policyname = row["policyname"]
            qual = row["qual"]
            with_check = row["with_check"]

            # Extract action from policy name suffix
            suffix = policyname[len(self.policy_name) + 1 :]  # +1 for underscore
            action = suffix.lower()

            # Convert PostgreSQL current_setting() back to :param syntax
            if action in result and action != "insert":
                if qual:
                    condition = self._convert_from_pg_condition(qual)
                    result[action].append(condition)
            elif action == "insert":
                if with_check:
                    condition = self._convert_from_pg_condition(with_check)
                    result[action].append(condition)

        return result

    def _convert_from_pg_condition(self, pg_condition: str) -> str:
        """Convert PostgreSQL current_setting() back to :param syntax.

        Args:
            pg_condition: PostgreSQL condition with current_setting() calls.

        Returns:
            Condition string with :param syntax.
        """
        # Replace current_setting('app.param', true) with :param
        return re.sub(
            r"current_setting\('app\.(\w+)'(?:,\s*true)?\)",
            r":\1",
            pg_condition,
        )

    async def _get_current_policy(
        self,
        driver: "BaseDriver",
        conn: Any,
    ) -> dict[str, Any]:
        """Get current policy from metadata table (MySQL/SQLite)."""
        select_sql = driver.convert_placeholders(
            """
            SELECT select_rules, insert_rules, update_rules, delete_rules,
                   auto_set, bypass_roles
            FROM _pykour_access_policies
            WHERE table_name = $1 AND policy_name = $2
            """,
            2,
        )
        rows = await driver.fetch_all(conn, select_sql, (self.table, self.policy_name))
        if not rows:
            return {}

        row = rows[0]
        return {
            "select": json.loads(row["select_rules"] or "[]"),
            "insert": json.loads(row["insert_rules"] or "[]"),
            "update": json.loads(row["update_rules"] or "[]"),
            "delete": json.loads(row["delete_rules"] or "[]"),
            "auto_set": json.loads(row["auto_set"] or "{}"),
            "bypass_roles": json.loads(row["bypass_roles"] or "[]"),
        }

    def reverse(self) -> "Operation":
        """Return the reverse operation."""
        if self._old_policy is None:
            raise ValueError("Cannot reverse AlterAccessPolicy without backup")
        return AlterAccessPolicy(
            self.table,
            self.policy_name,
            new_select=self._old_policy.get("select"),
            new_insert=self._old_policy.get("insert"),
            new_update=self._old_policy.get("update"),
            new_delete=self._old_policy.get("delete"),
            new_auto_set=self._old_policy.get("auto_set"),
            new_bypass_roles=self._old_policy.get("bypass_roles"),
        )

    def to_code(self) -> str:
        """Generate Python code for this operation."""
        parts = [f'"{self.table}"', f'"{self.policy_name}"']
        if self.new_select is not None:
            parts.append(f"new_select={self.new_select!r}")
        if self.new_insert is not None:
            parts.append(f"new_insert={self.new_insert!r}")
        if self.new_update is not None:
            parts.append(f"new_update={self.new_update!r}")
        if self.new_delete is not None:
            parts.append(f"new_delete={self.new_delete!r}")
        if self.new_auto_set is not None:
            parts.append(f"new_auto_set={self.new_auto_set!r}")
        if self.new_bypass_roles is not None:
            parts.append(f"new_bypass_roles={self.new_bypass_roles!r}")
        return f"op.alter_access_policy({', '.join(parts)})"
