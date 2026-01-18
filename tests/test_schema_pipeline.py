"""Tests for Schema validation pipeline."""

from __future__ import annotations

from typing import Any, Optional
from unittest.mock import MagicMock

import pytest

from pykour.schema.errors import ValidationError
from pykour.schema.fields import FieldInfo
from pykour.schema.pipeline import (
    FieldValidationStage,
    ModelAfterValidatorStage,
    ModelBeforeValidatorStage,
    ValidationContext,
    ValidationPipeline,
    is_optional,
)


class TestIsOptional:
    """Tests for is_optional helper function."""

    def test_optional_type_true(self) -> None:
        """Optional[str] should return True."""
        result = is_optional(Optional[str])
        assert result is True

    def test_union_with_none_true(self) -> None:
        """str | None should return True."""
        result = is_optional(str | None)
        assert result is True

    def test_non_optional_false(self) -> None:
        """str should return False."""
        result = is_optional(str)
        assert result is False

    def test_union_without_none_false(self) -> None:
        """str | int should return False."""
        result = is_optional(str | int)
        assert result is False

    def test_optional_int_true(self) -> None:
        """Optional[int] should return True."""
        result = is_optional(Optional[int])
        assert result is True

    def test_int_false(self) -> None:
        """int should return False."""
        result = is_optional(int)
        assert result is False


class TestValidationContext:
    """Tests for ValidationContext dataclass."""

    def test_init_with_required_fields(self) -> None:
        """Should initialize with required fields."""
        ctx = ValidationContext(
            data={"name": "Alice"},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )
        assert ctx.data == {"name": "Alice"}
        assert ctx.schema_fields == {}
        assert ctx.field_validators == {}
        assert ctx.model_validators == []

    def test_default_coercion_depth(self) -> None:
        """Default coercion_depth should be 0."""
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )
        assert ctx.coercion_depth == 0

    def test_default_errors_empty(self) -> None:
        """Default errors should be empty list."""
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )
        assert ctx.errors == []

    def test_default_validated_empty(self) -> None:
        """Default validated should be empty dict."""
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )
        assert ctx.validated == {}


class MockFieldInfo(FieldInfo):
    """Mock FieldInfo for testing.

    Extends FieldInfo but allows direct control over has_default behavior.
    """

    def __init__(
        self,
        alias: str | None = None,
        has_default: bool = False,
        default: Any = None,
        constraints: list | None = None,
    ) -> None:
        # Initialize parent with default if has_default is True
        if has_default:
            super().__init__(default=default, alias=alias)
        else:
            super().__init__(alias=alias)
        self._force_has_default = has_default
        self._force_default = default
        self._constraints = constraints or []

    @property
    def has_default(self) -> bool:
        """Override to return the forced value."""
        return self._force_has_default

    def get_default(self) -> Any:
        """Override to return the forced default."""
        return self._force_default

    def get_constraints(self) -> list:
        """Override to return the custom constraints."""
        return self._constraints


class MockValidatorInfo:
    """Mock ValidatorInfo for testing."""

    def __init__(self, mode: str, func: Any) -> None:
        self.mode = mode
        self.func = func


class TestModelBeforeValidatorStage:
    """Tests for ModelBeforeValidatorStage."""

    def test_execute_with_no_validators(self) -> None:
        """Should pass through when no validators."""
        stage = ModelBeforeValidatorStage()
        ctx = ValidationContext(
            data={"name": "Alice"},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )

        stage.execute(ctx)

        assert ctx.data == {"name": "Alice"}

    def test_execute_calls_before_validators(self) -> None:
        """Should call validators with mode='before'."""
        stage = ModelBeforeValidatorStage()

        def transform_data(data: dict) -> dict:
            data["transformed"] = True
            return data

        validator = MockValidatorInfo(mode="before", func=transform_data)
        ctx = ValidationContext(
            data={"name": "Alice"},
            schema_fields={},
            field_validators={},
            model_validators=[validator],  # type: ignore[list-item]
        )

        stage.execute(ctx)

        assert ctx.data["transformed"] is True

    def test_execute_skips_after_validators(self) -> None:
        """Should skip validators with mode='after'."""
        stage = ModelBeforeValidatorStage()

        def should_not_be_called(data: dict) -> dict:
            data["should_not_exist"] = True
            return data

        validator = MockValidatorInfo(mode="after", func=should_not_be_called)
        ctx = ValidationContext(
            data={"name": "Alice"},
            schema_fields={},
            field_validators={},
            model_validators=[validator],  # type: ignore[list-item]
        )

        stage.execute(ctx)

        assert "should_not_exist" not in ctx.data

    def test_execute_collects_errors_on_exception(self) -> None:
        """Should collect errors from failing validators."""
        stage = ModelBeforeValidatorStage()

        def failing_validator(data: dict) -> dict:
            raise ValueError("Validation failed")

        validator = MockValidatorInfo(mode="before", func=failing_validator)
        ctx = ValidationContext(
            data={"name": "Alice"},
            schema_fields={},
            field_validators={},
            model_validators=[validator],  # type: ignore[list-item]
        )

        with pytest.raises(ValidationError):
            stage.execute(ctx)


class TestFieldValidationStage:
    """Tests for FieldValidationStage."""

    def test_extract_value_from_data(self) -> None:
        """Should extract value by field name."""
        stage = FieldValidationStage()
        field_info = MockFieldInfo()
        ctx = ValidationContext(
            data={"name": "Alice"},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )

        value = stage._extract_value(ctx, "name", field_info)

        assert value == "Alice"

    def test_extract_value_with_alias(self) -> None:
        """Should extract value by alias if set."""
        stage = FieldValidationStage()
        field_info = MockFieldInfo(alias="user_name")
        ctx = ValidationContext(
            data={"user_name": "Bob"},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )

        value = stage._extract_value(ctx, "name", field_info)

        assert value == "Bob"

    def test_extract_value_uses_default(self) -> None:
        """Should use default when field missing."""
        stage = FieldValidationStage()
        field_info = MockFieldInfo(has_default=True, default="DefaultValue")
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )

        value = stage._extract_value(ctx, "name", field_info)

        assert value == "DefaultValue"

    def test_extract_value_missing_required_adds_error(self) -> None:
        """Should add error for missing required field."""
        stage = FieldValidationStage()
        field_info = MockFieldInfo(has_default=False)
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )

        value = stage._extract_value(ctx, "name", field_info)

        assert value is None
        assert len(ctx.errors) == 1
        assert ctx.errors[0].type == "value_error.missing"

    def test_coerce_type_success(self) -> None:
        """Should coerce value to target type."""
        stage = FieldValidationStage()
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )

        value = stage._coerce_type(ctx, "age", int, "30")

        assert value == 30
        assert isinstance(value, int)

    def test_coerce_type_failure_adds_error(self) -> None:
        """Should add error on coercion failure."""
        stage = FieldValidationStage()
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[],
        )

        value = stage._coerce_type(ctx, "age", int, "not_a_number")

        assert value is None
        assert len(ctx.errors) == 1
        assert ctx.errors[0].type == "type_error"

    def test_run_before_validators(self) -> None:
        """Should run 'before' field validators."""
        stage = FieldValidationStage()

        def uppercase(value: str) -> str:
            return value.upper()

        validator = MockValidatorInfo(mode="before", func=uppercase)
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={"name": [validator]},  # type: ignore[dict-item]
            model_validators=[],
        )

        result = stage._run_before_validators(ctx, "name", "alice")

        assert result == "ALICE"

    def test_run_after_validators(self) -> None:
        """Should run 'after' field validators."""
        stage = FieldValidationStage()

        def add_suffix(value: str) -> str:
            return value + "_processed"

        validator = MockValidatorInfo(mode="after", func=add_suffix)
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={"name": [validator]},  # type: ignore[dict-item]
            model_validators=[],
        )

        result = stage._run_after_validators(ctx, "name", "Alice", "Alice")

        assert result == "Alice_processed"


class TestModelAfterValidatorStage:
    """Tests for ModelAfterValidatorStage."""

    def test_init_stores_instance(self) -> None:
        """Should store schema instance."""
        mock_instance = MagicMock()
        stage = ModelAfterValidatorStage(mock_instance)

        assert stage._instance is mock_instance

    def test_execute_calls_after_validators(self) -> None:
        """Should call validators with mode='after'."""
        mock_instance = MagicMock()

        def after_validator(instance: Any) -> Any:
            instance.validated = True
            return instance

        validator = MockValidatorInfo(mode="after", func=after_validator)
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[validator],  # type: ignore[list-item]
        )

        stage = ModelAfterValidatorStage(mock_instance)
        stage.execute(ctx)

        assert mock_instance.validated is True

    def test_execute_skips_before_validators(self) -> None:
        """Should skip validators with mode='before'."""

        class SimpleInstance:
            pass

        instance = SimpleInstance()

        def before_validator(inst: Any) -> Any:
            inst.should_not_exist = True
            return inst

        validator = MockValidatorInfo(mode="before", func=before_validator)
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[validator],  # type: ignore[list-item]
        )

        stage = ModelAfterValidatorStage(instance)
        stage.execute(ctx)

        assert not hasattr(instance, "should_not_exist")

    def test_execute_raises_on_error(self) -> None:
        """Should raise ValidationError on validator failure."""
        mock_instance = MagicMock()

        def failing_validator(instance: Any) -> Any:
            raise ValueError("Validation failed")

        validator = MockValidatorInfo(mode="after", func=failing_validator)
        ctx = ValidationContext(
            data={},
            schema_fields={},
            field_validators={},
            model_validators=[validator],  # type: ignore[list-item]
        )

        stage = ModelAfterValidatorStage(mock_instance)

        with pytest.raises(ValidationError):
            stage.execute(ctx)


class TestValidationPipeline:
    """Tests for ValidationPipeline orchestration."""

    def test_init_creates_stages(self) -> None:
        """Should create pre-stages list."""
        pipeline = ValidationPipeline()

        assert len(pipeline._pre_stages) == 2
        assert isinstance(pipeline._pre_stages[0], ModelBeforeValidatorStage)
        assert isinstance(pipeline._pre_stages[1], FieldValidationStage)

    def test_validate_runs_all_stages(self) -> None:
        """Should run all stages in order."""
        pipeline = ValidationPipeline()

        field_info = MockFieldInfo(has_default=True, default="test")
        mock_instance = MagicMock()

        ctx = ValidationContext(
            data={},
            schema_fields={"name": (str, field_info)},
            field_validators={},
            model_validators=[],
        )

        pipeline.validate(ctx, mock_instance)

        assert "name" in ctx.validated

    def test_validate_sets_attributes(self) -> None:
        """Should set validated attributes on instance."""
        pipeline = ValidationPipeline()

        field_info = MockFieldInfo()

        class SimpleInstance:
            name: str = ""

        instance = SimpleInstance()

        ctx = ValidationContext(
            data={"name": "Alice"},
            schema_fields={"name": (str, field_info)},
            field_validators={},
            model_validators=[],
        )

        pipeline.validate(ctx, instance)

        assert instance.name == "Alice"

    def test_validate_raises_on_errors(self) -> None:
        """Should raise if errors collected before setting attrs."""
        pipeline = ValidationPipeline()

        field_info = MockFieldInfo(has_default=False)
        mock_instance = MagicMock()

        ctx = ValidationContext(
            data={},  # Missing required field
            schema_fields={"name": (str, field_info)},
            field_validators={},
            model_validators=[],
        )

        with pytest.raises(ValidationError) as exc_info:
            pipeline.validate(ctx, mock_instance)

        assert len(exc_info.value.errors) > 0


class TestFieldValidationStageNoneHandling:
    """Tests for None value handling in FieldValidationStage."""

    def test_is_optional_with_union_none(self) -> None:
        """is_optional should correctly identify str | None."""
        assert is_optional(str | None) is True
        assert is_optional(int | None) is True
        assert is_optional(str) is False

    def test_stage_execute_handles_missing_field(self) -> None:
        """Execute should collect error for missing required fields."""
        stage = FieldValidationStage()
        field_info = MockFieldInfo(has_default=False)
        ctx = ValidationContext(
            data={},  # name is missing
            schema_fields={"name": (str, field_info)},
            field_validators={},
            model_validators=[],
        )

        stage.execute(ctx)

        assert len(ctx.errors) == 1
        assert ctx.errors[0].type == "value_error.missing"

    def test_stage_execute_uses_default_for_missing(self) -> None:
        """Execute should use default value when field missing."""
        stage = FieldValidationStage()
        field_info = MockFieldInfo(has_default=True, default="default_name")
        ctx = ValidationContext(
            data={},  # name is missing, but has default
            schema_fields={"name": (str, field_info)},
            field_validators={},
            model_validators=[],
        )

        stage.execute(ctx)

        assert len(ctx.errors) == 0
        assert ctx.validated.get("name") == "default_name"
