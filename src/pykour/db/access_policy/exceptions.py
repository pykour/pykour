"""Exceptions for AccessPolicy module."""

from __future__ import annotations


class PolicyError(Exception):
    """Base exception for policy errors."""

    pass


class PolicyViolationError(PolicyError):
    """Raised when an operation violates a policy."""

    def __init__(
        self,
        message: str,
        *,
        table: str | None = None,
        action: str | None = None,
        policy_name: str | None = None,
    ) -> None:
        super().__init__(message)
        self.table = table
        self.action = action
        self.policy_name = policy_name


class PolicyContextMissingError(PolicyError):
    """Raised when policy context is required but not set."""

    def __init__(
        self,
        message: str = "Policy context is not set",
        *,
        required_keys: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.required_keys = required_keys or []


class PolicyConfigurationError(PolicyError):
    """Raised when policy is incorrectly configured."""

    pass
