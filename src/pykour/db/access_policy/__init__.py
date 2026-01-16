"""Access Policy module for row-level security."""

from pykour.db.access_policy.policy import AccessPolicy, PolicyRule, PolicyAction
from pykour.db.access_policy.context import (
    PolicyContextData,
    get_policy_context,
    set_policy_context,
    clear_policy_context,
    PolicyContextManager,
)
from pykour.db.access_policy.exceptions import (
    PolicyError,
    PolicyViolationError,
    PolicyContextMissingError,
    PolicyConfigurationError,
)
from pykour.db.access_policy.enforcer import (
    BasePolicyEnforcer,
    ApplicationLevelEnforcer,
    PostgreSQLNativeEnforcer,
    get_enforcer,
)
from pykour.db.access_policy.middleware import (
    AccessPolicyMiddleware,
    create_header_extractor,
    create_state_extractor,
)

__all__ = [
    # Policy definition
    "AccessPolicy",
    "PolicyRule",
    "PolicyAction",
    # Context management
    "PolicyContextData",
    "get_policy_context",
    "set_policy_context",
    "clear_policy_context",
    "PolicyContextManager",
    # Enforcers
    "BasePolicyEnforcer",
    "ApplicationLevelEnforcer",
    "PostgreSQLNativeEnforcer",
    "get_enforcer",
    # Middleware
    "AccessPolicyMiddleware",
    "create_header_extractor",
    "create_state_extractor",
    # Exceptions
    "PolicyError",
    "PolicyViolationError",
    "PolicyContextMissingError",
    "PolicyConfigurationError",
]
