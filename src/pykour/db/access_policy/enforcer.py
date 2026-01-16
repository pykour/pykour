"""Policy enforcer implementations for different database backends."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from pykour.db.access_policy.context import PolicyContextData
from pykour.db.access_policy.exceptions import PolicyContextMissingError
from pykour.db.access_policy.policy import AccessPolicy, PolicyAction, PolicyRule

if TYPE_CHECKING:
    pass

# Pattern for validating custom context key names
_VALID_KEY_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class BasePolicyEnforcer(ABC):
    """Base class for policy enforcement strategies.

    Subclasses implement database-specific enforcement mechanisms.
    """

    @abstractmethod
    async def setup_connection(
        self,
        conn: Any,
        context: PolicyContextData,
    ) -> None:
        """Set up connection for policy enforcement.

        Called before queries to set session variables, etc.

        Args:
            conn: Database connection.
            context: Current policy context.
        """
        ...

    @abstractmethod
    def apply_to_select(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Apply policy to a SELECT query.

        Args:
            sql: Original SQL query.
            args: Original query parameters.
            table: Table name being queried.
            policy: Access policy for the table.
            context: Current policy context.

        Returns:
            Tuple of (modified_sql, modified_args).
        """
        ...

    @abstractmethod
    def apply_to_insert(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
        values_data: list[dict[str, Any]],
    ) -> tuple[str, tuple[Any, ...], list[dict[str, Any]]]:
        """Apply policy to an INSERT query.

        Args:
            sql: Original SQL query.
            args: Original query parameters.
            table: Table name being inserted into.
            policy: Access policy for the table.
            context: Current policy context.
            values_data: List of row data dictionaries.

        Returns:
            Tuple of (modified_sql, modified_args, modified_values_data).
        """
        ...

    @abstractmethod
    def apply_to_update(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Apply policy to an UPDATE query.

        Args:
            sql: Original SQL query.
            args: Original query parameters.
            table: Table name being updated.
            policy: Access policy for the table.
            context: Current policy context.

        Returns:
            Tuple of (modified_sql, modified_args).
        """
        ...

    @abstractmethod
    def apply_to_delete(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Apply policy to a DELETE query.

        Args:
            sql: Original SQL query.
            args: Original query parameters.
            table: Table name being deleted from.
            policy: Access policy for the table.
            context: Current policy context.

        Returns:
            Tuple of (modified_sql, modified_args).
        """
        ...

    def _should_skip_enforcement(
        self,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> bool:
        """Check if enforcement should be skipped.

        Args:
            policy: Access policy.
            context: Current policy context.

        Returns:
            True if enforcement should be skipped.
        """
        if context.bypass_enforcement:
            return True
        if policy.should_bypass(context.roles):
            return True
        return False

    def _validate_context(
        self,
        rules: list[PolicyRule],
        context: PolicyContextData,
    ) -> None:
        """Validate that required context keys are present.

        Args:
            rules: List of policy rules.
            context: Current policy context.

        Raises:
            PolicyContextMissingError: If required keys are missing.
        """
        required_keys: set[str] = set()
        for rule in rules:
            required_keys.update(rule.get_required_context_keys())

        context_dict = context.to_dict()
        missing_keys = [key for key in required_keys if context_dict.get(key) is None]

        if missing_keys:
            raise PolicyContextMissingError(
                f"Missing required policy context keys: {missing_keys}",
                required_keys=missing_keys,
            )


class ApplicationLevelEnforcer(BasePolicyEnforcer):
    """Enforcer that injects WHERE clauses for MySQL/SQLite.

    This enforcer modifies queries at the application level by:
    - Adding WHERE clauses to SELECT, UPDATE, DELETE queries
    - Adding auto_set columns to INSERT queries
    """

    async def setup_connection(
        self,
        conn: Any,
        context: PolicyContextData,
    ) -> None:
        """No connection setup needed for application-level enforcement."""
        pass

    def apply_to_select(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Inject WHERE clause for SELECT."""
        if self._should_skip_enforcement(policy, context):
            return sql, args

        rules = policy.get_rules_for_action(PolicyAction.SELECT)
        if not rules:
            return sql, args

        self._validate_context(rules, context)
        return self._inject_where_clause(sql, args, rules, context)

    def apply_to_insert(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
        values_data: list[dict[str, Any]],
    ) -> tuple[str, tuple[Any, ...], list[dict[str, Any]]]:
        """Add auto_set columns to INSERT."""
        if self._should_skip_enforcement(policy, context):
            return sql, args, values_data

        if not policy.auto_set:
            return sql, args, values_data

        # Get auto-set values from context
        auto_values = policy.get_auto_set_values(context.to_dict())

        # Merge auto_set values into each row
        modified_values: list[dict[str, Any]] = []
        for row in values_data:
            new_row = row.copy()
            for col, val in auto_values.items():
                if col not in new_row:
                    new_row[col] = val
            modified_values.append(new_row)

        # We don't modify SQL here - the InsertQuery will rebuild it
        return sql, args, modified_values

    def apply_to_update(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Inject WHERE clause for UPDATE."""
        if self._should_skip_enforcement(policy, context):
            return sql, args

        rules = policy.get_rules_for_action(PolicyAction.UPDATE)
        if not rules:
            return sql, args

        self._validate_context(rules, context)
        return self._inject_where_clause(sql, args, rules, context)

    def apply_to_delete(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Inject WHERE clause for DELETE."""
        if self._should_skip_enforcement(policy, context):
            return sql, args

        rules = policy.get_rules_for_action(PolicyAction.DELETE)
        if not rules:
            return sql, args

        self._validate_context(rules, context)
        return self._inject_where_clause(sql, args, rules, context)

    def _inject_where_clause(
        self,
        sql: str,
        args: tuple[Any, ...],
        rules: list[PolicyRule],
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Inject WHERE conditions into SQL.

        Args:
            sql: Original SQL query.
            args: Original query parameters.
            rules: Policy rules to apply.
            context: Policy context.

        Returns:
            Tuple of (modified_sql, modified_args).
        """
        context_dict = context.to_dict()
        param_offset = len(args)
        conditions: list[str] = []
        new_params: list[Any] = []

        for rule in rules:
            rendered, params = rule.render(context_dict, param_offset)
            conditions.append(f"({rendered})")
            new_params.extend(params)
            param_offset += len(params)

        if not conditions:
            return sql, args

        # Build the WHERE clause addition
        policy_condition = " AND ".join(conditions)

        # Check if SQL already has WHERE clause
        sql_upper = sql.upper()
        where_pos = self._find_where_position(sql_upper)

        if where_pos != -1:
            # Insert after WHERE keyword
            insert_pos = where_pos + len("WHERE")
            modified_sql = (
                sql[:insert_pos] + f" ({policy_condition}) AND" + sql[insert_pos:]
            )
        else:
            # Find position to insert WHERE clause
            insert_pos = self._find_where_insert_position(sql_upper, sql)
            modified_sql = (
                sql[:insert_pos] + f" WHERE {policy_condition}" + sql[insert_pos:]
            )

        return modified_sql, args + tuple(new_params)

    def _skip_string_or_comment(self, sql: str, i: int) -> int:
        """Skip over string literals and SQL comments.

        Args:
            sql: SQL string (can be uppercase or original).
            i: Current position in the string.

        Returns:
            New position after skipping the string literal or comment,
            or the same position if not at a string/comment start.
        """
        if i >= len(sql):
            return i

        char = sql[i]

        # Skip single-quoted string literals (standard SQL strings)
        if char == "'":
            i += 1
            while i < len(sql):
                if sql[i] == "'":
                    # Check for escaped quote ('')
                    if i + 1 < len(sql) and sql[i + 1] == "'":
                        i += 2
                        continue
                    return i + 1  # Position after closing quote
                i += 1
            return i  # Unterminated string, return end

        # Skip double-quoted identifiers/strings
        if char == '"':
            i += 1
            while i < len(sql):
                if sql[i] == '"':
                    # Check for escaped quote ("")
                    if i + 1 < len(sql) and sql[i + 1] == '"':
                        i += 2
                        continue
                    return i + 1  # Position after closing quote
                i += 1
            return i  # Unterminated string, return end

        # Skip line comments (--)
        if char == "-" and i + 1 < len(sql) and sql[i + 1] == "-":
            i += 2
            while i < len(sql) and sql[i] not in ("\n", "\r"):
                i += 1
            return i

        # Skip block comments (/* */)
        if char == "/" and i + 1 < len(sql) and sql[i + 1] == "*":
            i += 2
            while i + 1 < len(sql):
                if sql[i] == "*" and sql[i + 1] == "/":
                    return i + 2  # Position after closing */
                i += 1
            return len(sql)  # Unterminated comment, return end

        return i  # Not a string or comment, return same position

    def _is_word_char(self, char: str) -> bool:
        """Check if character is a word character (alphanumeric or underscore).

        SQL identifiers can contain underscores, so we need to treat them
        as word characters for proper keyword boundary detection.

        Args:
            char: Single character to check.

        Returns:
            True if the character is alphanumeric or underscore.
        """
        return char.isalnum() or char == "_"

    def _find_where_position(self, sql_upper: str) -> int:
        """Find the position of WHERE keyword, ignoring subqueries.

        Properly skips over string literals and SQL comments to avoid
        misidentifying WHERE inside quoted strings or comments.

        Args:
            sql_upper: Uppercase SQL string.

        Returns:
            Position of WHERE keyword, or -1 if not found.
        """
        # Return early for strings too short to contain "WHERE"
        if len(sql_upper) < 5:
            return -1

        depth = 0
        i = 0
        while i <= len(sql_upper) - 5:
            # Skip string literals and comments
            new_i = self._skip_string_or_comment(sql_upper, i)
            if new_i != i:
                i = new_i
                continue

            if sql_upper[i] == "(":
                depth += 1
            elif sql_upper[i] == ")":
                depth -= 1
            elif depth == 0 and sql_upper[i : i + 5] == "WHERE":
                # Check it's a whole word (not part of an identifier like WHERE_col)
                before_ok = i == 0 or not self._is_word_char(sql_upper[i - 1])
                after_ok = i + 5 >= len(sql_upper) or not self._is_word_char(
                    sql_upper[i + 5]
                )
                if before_ok and after_ok:
                    return i
            i += 1
        return -1

    def _find_where_insert_position(self, sql_upper: str, sql: str) -> int:
        """Find position to insert WHERE clause.

        Looks for GROUP BY, HAVING, ORDER BY, LIMIT, OFFSET, or end of string.
        Properly skips over string literals and SQL comments.

        Args:
            sql_upper: Uppercase SQL string.
            sql: Original SQL string.

        Returns:
            Position to insert WHERE clause.
        """
        keywords = ["GROUP BY", "HAVING", "ORDER BY", "LIMIT", "OFFSET", "UNION"]
        depth = 0
        i = 0
        while i < len(sql_upper):
            # Skip string literals and comments
            new_i = self._skip_string_or_comment(sql_upper, i)
            if new_i != i:
                i = new_i
                continue

            if sql_upper[i] == "(":
                depth += 1
            elif sql_upper[i] == ")":
                depth -= 1
            elif depth == 0:
                for kw in keywords:
                    if sql_upper[i:].startswith(kw):
                        # Check it's a whole word (not part of an identifier)
                        before_ok = i == 0 or not self._is_word_char(sql_upper[i - 1])
                        after_ok = i + len(kw) >= len(
                            sql_upper
                        ) or not self._is_word_char(sql_upper[i + len(kw)])
                        if before_ok and after_ok:
                            return i
            i += 1
        return len(sql)


class PostgreSQLNativeEnforcer(BasePolicyEnforcer):
    """Enforcer that uses PostgreSQL's native RLS.

    For PostgreSQL, this enforcer:
    - Sets session variables that RLS policies reference
    - Still handles auto_set for INSERT operations
    """

    async def setup_connection(
        self,
        conn: Any,
        context: PolicyContextData,
    ) -> None:
        """Set session variables for RLS.

        Sets app.* variables that can be referenced by RLS policies
        using current_setting('app.xxx').

        Uses set_config() function with parameterized queries to prevent
        SQL injection attacks.

        Args:
            conn: asyncpg connection.
            context: Policy context.
        """
        # Set standard context values using parameterized queries
        tenant_value = str(context.tenant_id) if context.tenant_id is not None else ""
        await conn.execute(
            "SELECT set_config('app.tenant_id', $1, false)", tenant_value
        )

        user_value = str(context.user_id) if context.user_id is not None else ""
        await conn.execute("SELECT set_config('app.user_id', $1, false)", user_value)

        org_value = (
            str(context.organization_id) if context.organization_id is not None else ""
        )
        await conn.execute(
            "SELECT set_config('app.organization_id', $1, false)", org_value
        )

        # Set custom context values with key validation
        for key, value in context.custom.items():
            if not self._validate_key_name(key):
                raise ValueError(
                    f"Invalid custom context key name: '{key}'. "
                    "Key names must start with a letter or underscore and "
                    "contain only alphanumeric characters and underscores."
                )
            if value is not None:
                # Use parameterized query for the value
                # Note: The key name is validated above, so it's safe to use in string
                await conn.execute(
                    f"SELECT set_config('app.{key}', $1, false)", str(value)
                )

    def _validate_key_name(self, key: str) -> bool:
        """Validate that a key name is safe for use in SQL.

        Args:
            key: Key name to validate.

        Returns:
            True if the key name is valid.
        """
        return bool(_VALID_KEY_PATTERN.match(key))

    def apply_to_select(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Native RLS handles SELECT - no SQL modification needed."""
        # RLS policies handle filtering automatically
        return sql, args

    def apply_to_insert(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
        values_data: list[dict[str, Any]],
    ) -> tuple[str, tuple[Any, ...], list[dict[str, Any]]]:
        """Add auto_set columns to INSERT.

        Even with native RLS, we need to inject values for INSERT.
        """
        if self._should_skip_enforcement(policy, context):
            return sql, args, values_data

        if not policy.auto_set:
            return sql, args, values_data

        # Get auto-set values from context
        auto_values = policy.get_auto_set_values(context.to_dict())

        # Merge auto_set values into each row
        modified_values: list[dict[str, Any]] = []
        for row in values_data:
            new_row = row.copy()
            for col, val in auto_values.items():
                if col not in new_row:
                    new_row[col] = val
            modified_values.append(new_row)

        return sql, args, modified_values

    def apply_to_update(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Native RLS handles UPDATE - no SQL modification needed."""
        return sql, args

    def apply_to_delete(
        self,
        sql: str,
        args: tuple[Any, ...],
        table: str,
        policy: AccessPolicy,
        context: PolicyContextData,
    ) -> tuple[str, tuple[Any, ...]]:
        """Native RLS handles DELETE - no SQL modification needed."""
        return sql, args


def get_enforcer(driver_name: str) -> BasePolicyEnforcer:
    """Get the appropriate enforcer for a database driver.

    Args:
        driver_name: Name of the database driver (sqlite, postgresql, mysql).

    Returns:
        Appropriate PolicyEnforcer instance.
    """
    if driver_name == "postgresql":
        return PostgreSQLNativeEnforcer()
    return ApplicationLevelEnforcer()
