"""Validation pipeline for Schema validation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pykour.schema.errors import ErrorDetail, ValidationError
from pykour.schema.fields import MISSING
from pykour.schema.types import coerce_value

if TYPE_CHECKING:
    from pykour.schema.fields import FieldInfo
    from pykour.schema.validators import FieldValidatorInfo, ModelValidatorInfo


def is_optional(type_: type | Any) -> bool:
    """Check if a type annotation is Optional (Union with None).

    Args:
        type_: A type annotation (type, UnionType, or typing construct).

    Returns:
        True if the type annotation includes None.
    """
    from types import UnionType
    from typing import Union, get_args, get_origin

    origin = get_origin(type_)

    if origin is Union:
        return type(None) in get_args(type_)

    if isinstance(type_, UnionType):
        return type(None) in get_args(type_)

    return False


@dataclass
class ValidationContext:
    """Context for validation pipeline execution.

    Attributes:
        data: Input data dictionary.
        schema_fields: Field definitions {field_name: (type, FieldInfo)}.
        field_validators: Field validators {field_name: [FieldValidatorInfo]}.
        model_validators: Model validators list.
        coercion_depth: Current coercion depth for recursion protection.
        errors: Accumulated validation errors.
        validated: Validated field values.
    """

    data: dict[str, Any]
    schema_fields: dict[str, tuple[type, "FieldInfo"]]
    field_validators: dict[str, list["FieldValidatorInfo"]]
    model_validators: list["ModelValidatorInfo"]
    coercion_depth: int = 0
    errors: list[ErrorDetail] = field(default_factory=list)
    validated: dict[str, Any] = field(default_factory=dict)


class ValidationStage(ABC):
    """Abstract base class for validation stages."""

    @abstractmethod
    def execute(self, ctx: ValidationContext) -> None:
        """Execute this validation stage.

        Args:
            ctx: Validation context to operate on.
        """
        pass


class ModelBeforeValidatorStage(ValidationStage):
    """Run 'before' model validators on input data."""

    def execute(self, ctx: ValidationContext) -> None:
        """Execute before model validators."""
        for validator_info in ctx.model_validators:
            if validator_info.mode == "before":
                try:
                    ctx.data = validator_info.func(ctx.data)
                except (TypeError, ValueError) as e:
                    ctx.errors.append(
                        ErrorDetail(
                            loc=("body",),
                            msg=str(e),
                            type="value_error.model_validator",
                        )
                    )

        if ctx.errors:
            raise ValidationError(ctx.errors)


class FieldValidationStage(ValidationStage):
    """Validate all fields: extract values, coerce types, apply constraints."""

    def execute(self, ctx: ValidationContext) -> None:
        """Execute field validation for all fields."""
        for field_name, (field_type, field_info) in ctx.schema_fields.items():
            self._validate_field(ctx, field_name, field_type, field_info)

    def _validate_field(
        self,
        ctx: ValidationContext,
        field_name: str,
        field_type: type,
        field_info: "FieldInfo",
    ) -> None:
        """Validate a single field."""
        # Step 1: Extract value
        raw_value = self._extract_value(ctx, field_name, field_info)
        if raw_value is MISSING:
            return  # Error already added (field required but missing)

        # Step 2: Handle None for Optional types
        if raw_value is None:
            if is_optional(field_type):
                ctx.validated[field_name] = None
                return
            else:
                ctx.errors.append(
                    ErrorDetail(
                        loc=("body", field_name),
                        msg="Field cannot be None",
                        type="type_error.none_not_allowed",
                        input=raw_value,
                    )
                )
                return

        # Step 3: Run 'before' field validators
        raw_value = self._run_before_validators(ctx, field_name, raw_value)
        if raw_value is None:
            return  # Validator failed

        # Step 4: Type coercion
        value = self._coerce_type(ctx, field_name, field_type, raw_value)
        if value is None and not is_optional(field_type):
            return  # Coercion failed

        # Step 5: Constraint validation
        self._validate_constraints(ctx, field_name, field_info, value, raw_value)

        # Step 6: Run 'after' field validators
        value = self._run_after_validators(ctx, field_name, value, raw_value)

        ctx.validated[field_name] = value

    def _extract_value(
        self,
        ctx: ValidationContext,
        field_name: str,
        field_info: "FieldInfo",
    ) -> Any:
        """Extract field value from data or default.

        Returns:
            The field value, or MISSING sentinel if field is required but not provided.
        """
        key = field_info.alias or field_name

        if key in ctx.data:
            return ctx.data[key]
        elif field_info.has_default:
            return field_info.get_default()
        else:
            ctx.errors.append(
                ErrorDetail(
                    loc=("body", field_name),
                    msg="Field required",
                    type="value_error.missing",
                )
            )
            return MISSING

    def _run_before_validators(
        self,
        ctx: ValidationContext,
        field_name: str,
        raw_value: Any,
    ) -> Any:
        """Run 'before' field validators."""
        for validator_info in ctx.field_validators.get(field_name, []):
            if validator_info.mode == "before":
                try:
                    raw_value = validator_info.func(raw_value)
                except (TypeError, ValueError) as e:
                    ctx.errors.append(
                        ErrorDetail(
                            loc=("body", field_name),
                            msg=str(e),
                            type="value_error.field_validator",
                            input=raw_value,
                        )
                    )
                    return None  # Stop processing this field
        return raw_value

    def _coerce_type(
        self,
        ctx: ValidationContext,
        field_name: str,
        field_type: type,
        raw_value: Any,
    ) -> Any:
        """Coerce value to field type."""
        try:
            return coerce_value(raw_value, field_type, _depth=ctx.coercion_depth)
        except (TypeError, ValueError, RecursionError) as e:
            ctx.errors.append(
                ErrorDetail(
                    loc=("body", field_name),
                    msg=str(e),
                    type="type_error",
                    input=raw_value,
                )
            )
            return None

    def _validate_constraints(
        self,
        ctx: ValidationContext,
        field_name: str,
        field_info: "FieldInfo",
        value: Any,
        raw_value: Any,
    ) -> None:
        """Validate field constraints."""
        for constraint in field_info.get_constraints():
            try:
                constraint.validate(value, field_name)
            except ValueError as e:
                ctx.errors.append(
                    ErrorDetail(
                        loc=("body", field_name),
                        msg=str(e),
                        type=f"value_error.{constraint.__class__.__name__.lower()}",
                        input=raw_value,
                    )
                )

    def _run_after_validators(
        self,
        ctx: ValidationContext,
        field_name: str,
        value: Any,
        raw_value: Any,
    ) -> Any:
        """Run 'after' field validators."""
        for validator_info in ctx.field_validators.get(field_name, []):
            if validator_info.mode == "after":
                try:
                    value = validator_info.func(value)
                except (TypeError, ValueError) as e:
                    ctx.errors.append(
                        ErrorDetail(
                            loc=("body", field_name),
                            msg=str(e),
                            type="value_error.field_validator",
                            input=raw_value,
                        )
                    )
        return value


class ModelAfterValidatorStage(ValidationStage):
    """Run 'after' model validators on the schema instance."""

    def __init__(self, instance: Any) -> None:
        """Initialize with schema instance.

        Args:
            instance: The Schema instance being validated.
        """
        self._instance = instance

    def execute(self, ctx: ValidationContext) -> None:
        """Execute after model validators."""
        for validator_info in ctx.model_validators:
            if validator_info.mode == "after":
                try:
                    result = validator_info.func(self._instance)
                    # Model validator can return modified self or a new instance
                    if result is not None and result is not self._instance:
                        # Copy attributes from result
                        for field_name in ctx.schema_fields:
                            setattr(
                                self._instance, field_name, getattr(result, field_name)
                            )
                except (TypeError, ValueError) as e:
                    raise ValidationError(
                        [
                            ErrorDetail(
                                loc=("body",),
                                msg=str(e),
                                type="value_error.model_validator",
                            )
                        ]
                    )


class ValidationPipeline:
    """Orchestrates the validation process through stages.

    Example:
        pipeline = ValidationPipeline()
        ctx = ValidationContext(
            data={"name": "Alice", "age": 30},
            schema_fields=schema_class.__schema_fields__,
            field_validators=schema_class.__field_validators__,
            model_validators=schema_class.__model_validators__,
        )
        pipeline.validate(ctx, instance)
    """

    def __init__(self) -> None:
        """Initialize the validation pipeline."""
        self._pre_stages: list[ValidationStage] = [
            ModelBeforeValidatorStage(),
            FieldValidationStage(),
        ]

    def validate(self, ctx: ValidationContext, instance: Any) -> None:
        """Run the full validation pipeline.

        Args:
            ctx: Validation context with input data and field definitions.
            instance: Schema instance to populate with validated values.

        Raises:
            ValidationError: If validation fails.
        """
        # Run pre-instance stages
        for stage in self._pre_stages:
            stage.execute(ctx)

        # Check for accumulated errors before setting attributes
        if ctx.errors:
            raise ValidationError(ctx.errors)

        # Set validated attributes on instance
        for k, v in ctx.validated.items():
            setattr(instance, k, v)

        # Run post-instance stages
        after_stage = ModelAfterValidatorStage(instance)
        after_stage.execute(ctx)
