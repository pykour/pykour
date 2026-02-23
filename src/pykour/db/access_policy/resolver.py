"""Value resolver for auto-set column values."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pykour.db.access_policy.context import PolicyContextData


def _utc_now_naive() -> datetime:
    """Get current UTC time as a naive datetime (no timezone info).

    This is used for compatibility with databases that use TIMESTAMP
    without timezone (the default for most frameworks).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ValueResolver:
    """Resolves special values for auto-set columns.

    Supports the following special values:
        - ":now" - Current UTC time as naive datetime
        - ":user_id" - User ID from policy context
        - ":tenant_id" - Tenant ID from policy context
        - ":organization_id" - Organization ID from policy context
        - Any other string starting with ":" - Looked up in policy context
        - Any other string - Treated as a literal value

    Example:
        resolver = ValueResolver(context)
        value = resolver.resolve(":user_id")  # Returns context.user_id
        value = resolver.resolve(":now")  # Returns current UTC datetime (naive)
        value = resolver.resolve("literal")  # Returns "literal"
    """

    def __init__(self, context: "PolicyContextData | None" = None) -> None:
        """Initialize the resolver.

        Args:
            context: Policy context data for resolving context values.
        """
        self._context = context

    def resolve(self, value: str) -> Any:
        """Resolve a value string to an actual value.

        Args:
            value: The value string to resolve. Can be:
                - ":now" for current UTC time (naive datetime)
                - ":key" for a value from policy context
                - Any other string as a literal

        Returns:
            The resolved value.
        """
        if not value.startswith(":"):
            # Literal value
            return value

        key = value[1:]  # Remove leading ":"

        if key == "now":
            return _utc_now_naive()

        # Look up in context
        if self._context is None:
            return None

        return self._context.get(key)

    def resolve_for_insert(
        self,
        auto_now_add: bool,
        auto_now: bool,
        auto_set_on_insert: str | None,
        auto_set: str | None,
    ) -> Any | None:
        """Resolve value for INSERT operation.

        Args:
            auto_now_add: If True, return current UTC time (naive).
            auto_now: If True, return current UTC time (also applies to INSERT).
            auto_set_on_insert: Value to set on INSERT only.
            auto_set: Value to set on INSERT and UPDATE.

        Returns:
            The resolved value, or None if no auto-set is configured.
        """
        if auto_now_add or auto_now:
            return _utc_now_naive()

        if auto_set_on_insert:
            return self.resolve(auto_set_on_insert)

        if auto_set:
            return self.resolve(auto_set)

        return None

    def resolve_for_update(
        self,
        auto_now: bool,
        auto_set: str | None,
    ) -> Any | None:
        """Resolve value for UPDATE operation.

        Args:
            auto_now: If True, return current UTC time (naive).
            auto_set: Value to set on UPDATE.

        Returns:
            The resolved value, or None if no auto-set is configured.
        """
        if auto_now:
            return _utc_now_naive()

        if auto_set:
            return self.resolve(auto_set)

        return None
