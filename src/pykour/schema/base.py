"""Schema base class for validation."""

from typing import Any, ClassVar, get_type_hints

from pykour.schema.fields import MISSING, FieldInfo
from pykour.schema.pipeline import ValidationContext, ValidationPipeline
from pykour.schema.validators import (
    FieldValidatorInfo,
    ModelValidatorInfo,
    _MODEL_VALIDATOR_REGISTRY_ATTR,
    _VALIDATOR_REGISTRY_ATTR,
)


class SchemaMeta(type):
    """Metaclass for Schema that processes field annotations."""

    def __new__(
        mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any]
    ) -> type:
        cls = super().__new__(mcs, name, bases, namespace)

        if name != "Schema":
            # Collect field info from annotations and defaults
            cls.__schema_fields__ = mcs._collect_fields(cls)
            # Collect validators from class methods
            cls.__field_validators__ = mcs._collect_field_validators(cls, namespace)
            cls.__model_validators__ = mcs._collect_model_validators(cls, namespace)

        return cls

    @staticmethod
    def _collect_fields(cls: type) -> dict[str, tuple[type, FieldInfo]]:
        """Collect field type and metadata."""
        hints = get_type_hints(cls)
        fields: dict[str, tuple[type, FieldInfo]] = {}

        for field_name, field_type in hints.items():
            if field_name.startswith("_"):
                continue

            default = getattr(cls, field_name, MISSING)
            if isinstance(default, FieldInfo):
                fields[field_name] = (field_type, default)
            elif default is MISSING:
                field_info = FieldInfo()
                fields[field_name] = (field_type, field_info)
            else:
                field_info = FieldInfo(default=default)
                fields[field_name] = (field_type, field_info)

        return fields

    @staticmethod
    def _collect_field_validators(
        cls: type, namespace: dict[str, Any]
    ) -> dict[str, list[FieldValidatorInfo]]:
        """Collect field validators from class methods."""
        validators: dict[str, list[FieldValidatorInfo]] = {}

        # Check all methods in namespace and base classes
        for attr_name in dir(cls):
            try:
                attr = getattr(cls, attr_name)
            except AttributeError:
                continue

            # Handle classmethod/staticmethod wrapped functions
            func = attr
            if hasattr(attr, "__func__"):
                func = attr.__func__

            # Check for validator registry on the attribute
            validator_infos = getattr(func, _VALIDATOR_REGISTRY_ATTR, None)
            if validator_infos:
                for info in validator_infos:
                    for field_name in info.field_names:
                        if field_name not in validators:
                            validators[field_name] = []
                        # Store the callable (bound method or function)
                        validators[field_name].append(
                            FieldValidatorInfo(
                                func=attr,
                                field_names=info.field_names,
                                mode=info.mode,
                                check_fields=info.check_fields,
                            )
                        )

        return validators

    @staticmethod
    def _collect_model_validators(
        cls: type, namespace: dict[str, Any]
    ) -> list[ModelValidatorInfo]:
        """Collect model validators from class methods."""
        validators: list[ModelValidatorInfo] = []

        for attr_name in dir(cls):
            try:
                attr = getattr(cls, attr_name)
            except AttributeError:
                continue

            # Handle classmethod/staticmethod wrapped functions
            func = attr
            if hasattr(attr, "__func__"):
                func = attr.__func__

            validator_infos = getattr(func, _MODEL_VALIDATOR_REGISTRY_ATTR, None)
            if validator_infos:
                for info in validator_infos:
                    validators.append(ModelValidatorInfo(func=attr, mode=info.mode))

        return validators


class Schema(metaclass=SchemaMeta):
    """Base class for validated schemas."""

    __schema_fields__: ClassVar[dict[str, tuple[type, FieldInfo]]]
    __field_validators__: ClassVar[dict[str, list[FieldValidatorInfo]]]
    __model_validators__: ClassVar[list[ModelValidatorInfo]]

    # Shared pipeline instance for all Schema subclasses
    _pipeline: ClassVar[ValidationPipeline] = ValidationPipeline()

    def __init__(self, _coercion_depth: int = 0, **data: Any) -> None:
        """Initialize and validate schema data.

        Args:
            _coercion_depth: Internal recursion depth for type coercion.
            **data: Field values to validate.

        Raises:
            ValidationError: If validation fails.
        """
        self._coercion_depth = _coercion_depth

        ctx = ValidationContext(
            data=data,
            schema_fields=self.__schema_fields__,
            field_validators=getattr(self.__class__, "__field_validators__", {}),
            model_validators=getattr(self.__class__, "__model_validators__", []),
            coercion_depth=_coercion_depth,
        )

        self._pipeline.validate(ctx, self)

    def model_dump(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {name: getattr(self, name) for name in self.__schema_fields__}

    def __repr__(self) -> str:
        fields = ", ".join(
            f"{name}={getattr(self, name)!r}" for name in self.__schema_fields__
        )
        return f"{self.__class__.__name__}({fields})"

    @classmethod
    def _create_with_depth(cls, data: dict[str, Any], depth: int) -> "Schema":
        """Create a Schema instance with a specified coercion depth.

        This is used internally by the type coercion system to track
        recursion depth and prevent circular reference DoS attacks.

        Args:
            data: Dictionary of field values.
            depth: Current recursion depth.

        Returns:
            New Schema instance.
        """
        return cls(_coercion_depth=depth, **data)
