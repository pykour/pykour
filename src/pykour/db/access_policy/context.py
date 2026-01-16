"""Policy context management using contextvars for async-safe request-scoped storage."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PolicyContextData:
    """Request-scoped policy context data.

    Stores authentication and authorization information for the current request
    that is used to enforce access policies on database queries.

    Attributes:
        tenant_id: Tenant identifier for multi-tenant applications.
        user_id: User identifier for user-based access control.
        organization_id: Organization identifier for org-based access control.
        roles: List of role names for the current user.
        custom: Dictionary for custom context values.
        bypass_enforcement: If True, skip policy enforcement (for admin operations).
    """

    tenant_id: Any = None
    user_id: Any = None
    organization_id: Any = None
    roles: list[str] = field(default_factory=list)
    custom: dict[str, Any] = field(default_factory=dict)
    bypass_enforcement: bool = False

    def get(self, key: str) -> Any:
        """Get a context value by key.

        Looks up the key first as an attribute, then in custom dict.
        The 'custom' and 'bypass_enforcement' attributes are excluded from
        direct lookup as they are internal implementation details.

        Args:
            key: The context key to retrieve.

        Returns:
            The value for the key, or None if not found.
        """
        if hasattr(self, key) and key not in ("custom", "bypass_enforcement"):
            value = getattr(self, key)
            if value is not None:
                return value
        return self.custom.get(key)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for query parameter substitution.

        Returns:
            Dictionary containing all context values.
        """
        result: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
        }
        result.update(self.custom)
        return result


# Context variable for async-safe storage
_policy_context: ContextVar[PolicyContextData | None] = ContextVar(
    "policy_context",
    default=None,
)


def get_policy_context() -> PolicyContextData | None:
    """Get the current policy context.

    Returns:
        The current PolicyContextData, or None if not set.
    """
    return _policy_context.get()


def set_policy_context(
    *,
    tenant_id: Any = None,
    user_id: Any = None,
    organization_id: Any = None,
    roles: list[str] | None = None,
    bypass_enforcement: bool = False,
    **custom: Any,
) -> PolicyContextData:
    """Set the policy context for the current async context.

    Creates a new PolicyContextData and sets it as the current context.

    Args:
        tenant_id: Tenant identifier.
        user_id: User identifier.
        organization_id: Organization identifier.
        roles: List of role names.
        bypass_enforcement: If True, skip policy enforcement.
        **custom: Additional custom context values.

    Returns:
        The newly created PolicyContextData.

    Example:
        set_policy_context(tenant_id="t123", user_id="u456")
        ctx = get_policy_context()
        assert ctx.tenant_id == "t123"
    """
    ctx = PolicyContextData(
        tenant_id=tenant_id,
        user_id=user_id,
        organization_id=organization_id,
        roles=roles or [],
        custom=custom,
        bypass_enforcement=bypass_enforcement,
    )
    _policy_context.set(ctx)
    return ctx


def clear_policy_context() -> None:
    """Clear the policy context.

    Sets the context to None for the current async context.
    """
    _policy_context.set(None)


class PolicyContextManager:
    """Context manager for temporarily setting policy context.

    Provides a clean way to set policy context for a block of code,
    automatically restoring the previous context on exit.

    Example:
        with PolicyContextManager(tenant_id="t123"):
            orders = await db.select("*").from_("orders").fetch_all()
        # Context is automatically cleared after the block
    """

    def __init__(
        self,
        *,
        tenant_id: Any = None,
        user_id: Any = None,
        organization_id: Any = None,
        roles: list[str] | None = None,
        bypass_enforcement: bool = False,
        **custom: Any,
    ) -> None:
        """Initialize the context manager.

        Args:
            tenant_id: Tenant identifier.
            user_id: User identifier.
            organization_id: Organization identifier.
            roles: List of role names.
            bypass_enforcement: If True, skip policy enforcement.
            **custom: Additional custom context values.
        """
        self._tenant_id = tenant_id
        self._user_id = user_id
        self._organization_id = organization_id
        self._roles = roles or []
        self._bypass_enforcement = bypass_enforcement
        self._custom = custom
        self._token: Token[PolicyContextData | None] | None = None

    def __enter__(self) -> PolicyContextData:
        """Enter the context and set policy context.

        Returns:
            The newly created PolicyContextData.
        """
        ctx = PolicyContextData(
            tenant_id=self._tenant_id,
            user_id=self._user_id,
            organization_id=self._organization_id,
            roles=self._roles,
            custom=self._custom,
            bypass_enforcement=self._bypass_enforcement,
        )
        self._token = _policy_context.set(ctx)
        return ctx

    def __exit__(self, *args: Any) -> None:
        """Exit the context and restore previous policy context."""
        if self._token is not None:
            _policy_context.reset(self._token)

    async def __aenter__(self) -> PolicyContextData:
        """Async enter - same as sync enter."""
        return self.__enter__()

    async def __aexit__(self, *args: Any) -> None:
        """Async exit - same as sync exit."""
        self.__exit__(*args)
