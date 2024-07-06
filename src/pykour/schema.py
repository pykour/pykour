from __future__ import annotations
from abc import ABCMeta
from typing import Any, Dict, get_type_hints, Type, get_origin, get_args


class BaseSchemaMetaclass(ABCMeta):
    def __new__(mcs, cls_name: str, bases, attrs, **kwargs: Any) -> type:
        fields = {key: value for key, value in attrs.items() if not key.startswith("_")}
        validators = {key: value for key, value in attrs.items() if hasattr(value, "__validator__")}

        cls = super().__new__(mcs, cls_name, bases, attrs, **kwargs)
        cls.__fields__ = fields  # type: ignore[attr-defined]
        cls.__validators__ = validators  # type: ignore[attr-defined]
        return cls


class BaseSchema(metaclass=BaseSchemaMetaclass):
    """Base class for schema."""

    def __init__(self, /, **data: Any) -> None:
        self._validate(data)
        self._set_attributes(data)

    def _set_attributes(self, data: Dict[str, Any]) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def _validate(self, data: Dict[str, Any]) -> None:
        for validator_name, validator_fn in self.__class__.__validators__.items():  # type: ignore[attr-defined]
            field_name = validator_fn.__validator__
            if field_name in data:
                value = data[field_name]
                validator_fn(self, value)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaseSchema:
        """
        Create instance from dictionary.

        Args:
            data: Dictionary with data.
        Returns:
            Instance of schema.
        """
        init_data = {}
        field_types = get_type_hints(cls)

        for field, field_type in field_types.items():
            if field in data:
                value = data[field]
                init_data[field] = cls._convert_value(field_type, value)
            else:
                init_data[field] = None

        return cls(**init_data)

    @staticmethod
    def _convert_value(field_type: Type, value: Any) -> Any:
        origin = get_origin(field_type)
        args = get_args(field_type)

        if isinstance(value, dict):
            if origin is not None and issubclass(origin, dict):
                return value
            elif isinstance(field_type, type) and issubclass(field_type, BaseSchema):
                return field_type.from_dict(value)
            else:
                return value
        elif isinstance(value, list) and origin is list:
            inner_type = args[0]
            return [BaseSchema._convert_value(inner_type, item) for item in value]
        else:
            return value
