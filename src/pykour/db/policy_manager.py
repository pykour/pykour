"""Access policy management for Pykour database."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pykour.db.access_policy.enforcer import BasePolicyEnforcer
    from pykour.db.access_policy.policy import AccessPolicy


class AccessPolicyManager:
    """Manages access policies for database tables.

    This class handles:
    - Table and policy registration
    - Policy lookup by table name
    - Policy enforcer initialization
    - Policy context retrieval
    - Table class storage for auto-set column access

    Example:
        manager = AccessPolicyManager()

        # Register a table class
        manager.register_table(UserTable)

        # Register multiple table classes at once
        manager.register_tables([UserTable, OrderTable, ProductTable])

        # Or register a policy directly
        manager.register_policy("orders", AccessPolicy(
            select=["tenant_id = :tenant_id"],
        ))

        # Get policy for a table
        policy = manager.get_policy("orders")

        # Get table class for auto-set columns
        table_class = manager.get_table_class("orders")
    """

    def __init__(self, enable_policies: bool = True) -> None:
        """Initialize the policy manager.

        Args:
            enable_policies: Whether to enable access policies.
        """
        self._enable_policies = enable_policies
        self._table_policies: dict[str, AccessPolicy] = {}
        self._table_classes: dict[str, type] = {}
        self._policy_enforcer: BasePolicyEnforcer | None = None

    @property
    def enabled(self) -> bool:
        """Check if access policies are enabled."""
        return self._enable_policies

    @property
    def enforcer(self) -> "BasePolicyEnforcer | None":
        """Get the policy enforcer."""
        return self._policy_enforcer

    @property
    def table_policies(self) -> dict[str, "AccessPolicy"]:
        """Get all registered table policies."""
        return self._table_policies

    def initialize_enforcer(self, driver_name: str) -> None:
        """Initialize the policy enforcer for a specific database driver.

        Args:
            driver_name: Name of the database driver (sqlite, postgresql, mysql).
        """
        if not self._enable_policies:
            return

        from pykour.db.access_policy.enforcer import get_enforcer

        self._policy_enforcer = get_enforcer(driver_name)

    def register_table(self, table_class: type) -> None:
        """Register a table class and its access policy.

        The table class should have:
        - __tablename__: Table name (optional, defaults to class name lowercased)
        - _access_policy: AccessPolicy instance (from Meta class or __access_policy__)

        Args:
            table_class: A Table subclass with optional access policy.
        """
        tablename = getattr(table_class, "__tablename__", None)
        if tablename is None:
            tablename = table_class.__name__.lower()

        # Store the table class for auto-set column access
        self._table_classes[tablename] = table_class

        # First check _access_policy (set by TableMeta from Meta.access_policy or __access_policy__)
        policy = getattr(table_class, "_access_policy", None)
        # Fall back to __access_policy__ for backwards compatibility
        if policy is None:
            policy = getattr(table_class, "__access_policy__", None)
        if policy is not None:
            self._table_policies[tablename] = policy

    def register_tables(self, table_classes: list[type]) -> None:
        """Register multiple table classes at once.

        Args:
            table_classes: List of Table subclasses to register.

        Example:
            manager.register_tables([UserTable, OrderTable, ProductTable])
        """
        for table_class in table_classes:
            self.register_table(table_class)

    def register_policy(self, table_name: str, policy: "AccessPolicy") -> None:
        """Register an access policy for a table.

        Args:
            table_name: Name of the table.
            policy: AccessPolicy instance.
        """
        self._table_policies[table_name] = policy

    def get_policy(self, table_name: str) -> "AccessPolicy | None":
        """Get the access policy for a table.

        Args:
            table_name: Name of the table.

        Returns:
            AccessPolicy or None if not registered.
        """
        return self._table_policies.get(table_name)

    def get_table_class(self, table_name: str) -> type | None:
        """Get the table class for a table.

        Args:
            table_name: Name of the table.

        Returns:
            Table class or None if not registered.
        """
        return self._table_classes.get(table_name)

    def get_policy_context(self) -> Any:
        """Get the current policy context.

        Returns:
            Policy context dict from thread-local storage.
        """
        from pykour.db.access_policy.context import get_policy_context

        return get_policy_context()

    def get_policy_kwargs(self) -> dict[str, Any]:
        """Get kwargs for policy-enabled query builders.

        Returns:
            Dict with policy_enforcer, table_policies, table_classes,
            and get_policy_context.
        """
        return {
            "policy_enforcer": self._policy_enforcer,
            "table_policies": self._table_policies,
            "table_classes": self._table_classes,
            "get_policy_context": self.get_policy_context,
        }
