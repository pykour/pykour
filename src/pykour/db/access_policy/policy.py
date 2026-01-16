"""AccessPolicy and PolicyRule classes for defining row-level security policies."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PolicyAction(str, Enum):
    """Actions that can be controlled by a policy."""

    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    ALL = "all"


@dataclass
class PolicyRule:
    """A single policy rule with a condition expression.

    The condition uses named parameters like :tenant_id, :user_id
    which are resolved from the PolicyContext at query time.

    Example:
        PolicyRule("tenant_id = :tenant_id")
        PolicyRule("user_id = :user_id OR is_public = true")
    """

    condition: str

    # Negative lookbehind (?<!:) excludes PostgreSQL type casts (e.g., value::text)
    _PARAM_PATTERN = re.compile(r"(?<!:):(\w+)")

    def get_required_context_keys(self) -> set[str]:
        """Extract required context keys from the condition.

        Returns:
            Set of parameter names referenced in the condition.

        Example:
            >>> rule = PolicyRule("tenant_id = :tenant_id AND user_id = :user_id")
            >>> rule.get_required_context_keys()
            {'tenant_id', 'user_id'}
        """
        return set(self._PARAM_PATTERN.findall(self.condition))

    def render(
        self,
        context: dict[str, Any],
        param_offset: int = 0,
    ) -> tuple[str, list[Any]]:
        """Render the condition with placeholder replacement.

        Replaces :param with $N style placeholders and returns the values.

        Args:
            context: Dictionary of context values.
            param_offset: Starting parameter index (for combining with existing params).

        Returns:
            Tuple of (rendered_condition, param_values).

        Raises:
            ValueError: If a required context key is missing.

        Example:
            >>> rule = PolicyRule("tenant_id = :tenant_id")
            >>> rule.render({"tenant_id": "t123"}, param_offset=2)
            ('tenant_id = $3', ['t123'])
        """
        params: list[Any] = []
        current_index = param_offset

        def replace_param(match: re.Match[str]) -> str:
            nonlocal current_index
            param_name = match.group(1)
            if param_name not in context:
                raise ValueError(
                    f"Missing required context key '{param_name}' "
                    f"in policy condition: {self.condition}"
                )
            value = context[param_name]
            if value is None:
                raise ValueError(
                    f"Context key '{param_name}' is None "
                    f"in policy condition: {self.condition}. "
                    f"Policy parameters must have non-None values."
                )
            params.append(value)
            current_index += 1
            return f"${current_index}"

        rendered = self._PARAM_PATTERN.sub(replace_param, self.condition)
        return rendered, params


@dataclass
class AccessPolicy:
    """Access policy definition for a table.

    Defines row-level access control rules for SELECT, INSERT, UPDATE, and DELETE
    operations. Supports automatic value injection for INSERT operations.

    Example:
        policy = AccessPolicy(
            name="orders_tenant_policy",
            select=["tenant_id = :tenant_id"],
            insert=["tenant_id = :tenant_id"],
            update=["tenant_id = :tenant_id", "user_id = :user_id"],
            delete=["tenant_id = :tenant_id", "user_id = :user_id"],
            auto_set={"tenant_id": ":tenant_id"},
            bypass_roles=["admin"],
        )

    Attributes:
        name: Policy name (used for migration and debugging).
        select: List of conditions for SELECT queries.
        insert: List of conditions to validate on INSERT.
        update: List of conditions for UPDATE queries.
        delete: List of conditions for DELETE queries.
        auto_set: Dict mapping column names to context keys for auto-insertion.
        bypass_roles: List of roles that bypass this policy.
    """

    name: str = ""
    select: list[str] = field(default_factory=list)
    insert: list[str] = field(default_factory=list)
    update: list[str] = field(default_factory=list)
    delete: list[str] = field(default_factory=list)
    auto_set: dict[str, str] = field(default_factory=dict)
    bypass_roles: list[str] = field(default_factory=list)

    def get_rules_for_action(self, action: PolicyAction) -> list[PolicyRule]:
        """Get policy rules for a specific action.

        Args:
            action: The action type to get rules for.

        Returns:
            List of PolicyRule objects for the action.
        """
        conditions: list[str] = []

        if action == PolicyAction.SELECT:
            conditions = self.select
        elif action == PolicyAction.INSERT:
            conditions = self.insert
        elif action == PolicyAction.UPDATE:
            conditions = self.update
        elif action == PolicyAction.DELETE:
            conditions = self.delete
        elif action == PolicyAction.ALL:
            # Combine all unique conditions
            seen: set[str] = set()
            for cond_list in [self.select, self.insert, self.update, self.delete]:
                for cond in cond_list:
                    if cond not in seen:
                        conditions.append(cond)
                        seen.add(cond)

        return [PolicyRule(cond) for cond in conditions]

    def get_all_required_context_keys(self) -> set[str]:
        """Get all context keys required by this policy.

        Returns:
            Set of all parameter names referenced across all rules.
        """
        keys: set[str] = set()

        for action in [
            PolicyAction.SELECT,
            PolicyAction.INSERT,
            PolicyAction.UPDATE,
            PolicyAction.DELETE,
        ]:
            for rule in self.get_rules_for_action(action):
                keys.update(rule.get_required_context_keys())

        # Also include keys from auto_set
        for value in self.auto_set.values():
            if value.startswith(":"):
                keys.add(value[1:])

        return keys

    def get_auto_set_values(self, context: dict[str, Any]) -> dict[str, Any]:
        """Get values to auto-set on INSERT based on context.

        Args:
            context: Dictionary of context values.

        Returns:
            Dictionary mapping column names to resolved values.

        Raises:
            KeyError: If a required context key is missing.

        Example:
            >>> policy = AccessPolicy(auto_set={"tenant_id": ":tenant_id"})
            >>> policy.get_auto_set_values({"tenant_id": "t123"})
            {'tenant_id': 't123'}
        """
        result: dict[str, Any] = {}
        for column, value_spec in self.auto_set.items():
            if value_spec.startswith(":"):
                key = value_spec[1:]
                if key not in context:
                    raise KeyError(
                        f"Missing required context key '{key}' for auto_set column '{column}'"
                    )
                result[column] = context[key]
            else:
                # Literal value
                result[column] = value_spec
        return result

    def should_bypass(self, roles: list[str]) -> bool:
        """Check if the given roles should bypass this policy.

        Args:
            roles: List of role names for the current user.

        Returns:
            True if any role is in bypass_roles.
        """
        if not self.bypass_roles:
            return False
        return bool(set(roles) & set(self.bypass_roles))
