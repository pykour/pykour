"""Constraint validators and custom validator decorators."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Literal


class Constraint:
    """Base constraint class."""

    def validate(self, value: Any, field_name: str) -> None:
        """Validate value, raise ValueError if invalid."""
        raise NotImplementedError


# Type alias for validator functions
ValidatorFunc = Callable[..., Any]


@dataclass
class FieldValidatorInfo:
    """Information about a field validator."""

    func: ValidatorFunc
    field_names: tuple[str, ...]
    mode: Literal["before", "after"] = "after"
    check_fields: bool = True

    def __hash__(self) -> int:
        func = self.func
        if isinstance(func, classmethod):
            func = func.__func__
        func_name = getattr(func, "__name__", str(id(func)))
        return hash((func_name, self.field_names, self.mode))


@dataclass
class ModelValidatorInfo:
    """Information about a model validator."""

    func: ValidatorFunc
    mode: Literal["before", "after"] = "after"

    def __hash__(self) -> int:
        func = self.func
        if isinstance(func, classmethod):
            func = func.__func__
        func_name = getattr(func, "__name__", str(id(func)))
        return hash((func_name, self.mode))


# Registry for validators (used by metaclass)
_VALIDATOR_REGISTRY_ATTR = "__pykour_validators__"
_MODEL_VALIDATOR_REGISTRY_ATTR = "__pykour_model_validators__"


def field_validator(
    *fields: str,
    mode: Literal["before", "after"] = "after",
    check_fields: bool = True,
) -> Callable[[ValidatorFunc], ValidatorFunc]:
    """Decorator for field validators.

    Field validators are called for specific fields during validation.
    They can transform or validate field values.

    Args:
        *fields: Names of fields to validate.
        mode: When to run the validator:
            - "before": Before type coercion (receives raw input)
            - "after": After type coercion (receives coerced value)
        check_fields: Whether to check that fields exist on the model.

    Returns:
        Decorator function.

    Example:
        class UserSchema(Schema):
            name: str
            email: str

            @field_validator("name")
            @classmethod
            def validate_name(cls, v: str) -> str:
                if not v.strip():
                    raise ValueError("Name cannot be empty")
                return v.strip()

            @field_validator("email")
            @classmethod
            def validate_email(cls, v: str) -> str:
                if "@" not in v:
                    raise ValueError("Invalid email format")
                return v.lower()
    """
    if not fields:
        raise ValueError("At least one field name must be provided")

    def decorator(func: ValidatorFunc) -> ValidatorFunc:
        # Handle classmethod wrapper
        target = func
        if isinstance(func, classmethod):
            target = func.__func__

        # Store validator info on the function
        if not hasattr(target, _VALIDATOR_REGISTRY_ATTR):
            setattr(target, _VALIDATOR_REGISTRY_ATTR, [])

        getattr(target, _VALIDATOR_REGISTRY_ATTR).append(
            FieldValidatorInfo(
                func=func,
                field_names=fields,
                mode=mode,
                check_fields=check_fields,
            )
        )
        return func

    return decorator


def model_validator(
    *,
    mode: Literal["before", "after"] = "after",
) -> Callable[[ValidatorFunc], ValidatorFunc]:
    """Decorator for model validators.

    Model validators are called for the entire model data.
    They can validate relationships between fields or transform the entire data.

    Args:
        mode: When to run the validator:
            - "before": Before field validation (receives raw input dict)
            - "after": After field validation (receives the model instance)

    Returns:
        Decorator function.

    Example:
        class PasswordSchema(Schema):
            password: str
            password_confirm: str

            @model_validator(mode="after")
            @classmethod
            def passwords_match(cls, model: "PasswordSchema") -> "PasswordSchema":
                if model.password != model.password_confirm:
                    raise ValueError("Passwords do not match")
                return model

        class SignupSchema(Schema):
            username: str
            email: str

            @model_validator(mode="before")
            @classmethod
            def preprocess(cls, data: dict) -> dict:
                if "username" in data:
                    data["username"] = data["username"].lower()
                return data
    """

    def decorator(func: ValidatorFunc) -> ValidatorFunc:
        # Handle classmethod wrapper
        target = func
        if isinstance(func, classmethod):
            target = func.__func__

        if not hasattr(target, _MODEL_VALIDATOR_REGISTRY_ATTR):
            setattr(target, _MODEL_VALIDATOR_REGISTRY_ATTR, [])

        getattr(target, _MODEL_VALIDATOR_REGISTRY_ATTR).append(
            ModelValidatorInfo(func=func, mode=mode)
        )
        return func

    return decorator


class Ge(Constraint):
    """Greater than or equal constraint."""

    def __init__(self, limit: int | float) -> None:
        self.limit = limit

    def validate(self, value: Any, field_name: str) -> None:
        if value < self.limit:
            raise ValueError(f"'{field_name}' must be >= {self.limit}")


class Gt(Constraint):
    """Greater than constraint."""

    def __init__(self, limit: int | float) -> None:
        self.limit = limit

    def validate(self, value: Any, field_name: str) -> None:
        if value <= self.limit:
            raise ValueError(f"'{field_name}' must be > {self.limit}")


class Le(Constraint):
    """Less than or equal constraint."""

    def __init__(self, limit: int | float) -> None:
        self.limit = limit

    def validate(self, value: Any, field_name: str) -> None:
        if value > self.limit:
            raise ValueError(f"'{field_name}' must be <= {self.limit}")


class Lt(Constraint):
    """Less than constraint."""

    def __init__(self, limit: int | float) -> None:
        self.limit = limit

    def validate(self, value: Any, field_name: str) -> None:
        if value >= self.limit:
            raise ValueError(f"'{field_name}' must be < {self.limit}")


class MinLength(Constraint):
    """Minimum length constraint for strings/lists."""

    def __init__(self, length: int) -> None:
        self.length = length

    def validate(self, value: Any, field_name: str) -> None:
        if len(value) < self.length:
            raise ValueError(f"'{field_name}' length must be >= {self.length}")


class MaxLength(Constraint):
    """Maximum length constraint for strings/lists."""

    def __init__(self, length: int) -> None:
        self.length = length

    def validate(self, value: Any, field_name: str) -> None:
        if len(value) > self.length:
            raise ValueError(f"'{field_name}' length must be <= {self.length}")


class Pattern(Constraint):
    """Regex pattern constraint."""

    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        self._regex = re.compile(pattern)

    def validate(self, value: Any, field_name: str) -> None:
        if not self._regex.match(str(value)):
            raise ValueError(f"'{field_name}' does not match pattern '{self.pattern}'")
