"""Type coercion utilities."""

from datetime import date, datetime
from typing import Any, Union, get_args, get_origin
from uuid import UUID


# Maximum recursion depth for nested schema coercion
_MAX_COERCION_DEPTH = 100


def _coerce_int(value: Any) -> int:
    """Coerce value to int."""
    if isinstance(value, bool):
        raise TypeError("Boolean is not a valid integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value)
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise TypeError("Float with decimal part cannot be coerced to int")
    raise TypeError(f"Cannot coerce {type(value).__name__} to int")


def _coerce_float(value: Any) -> float:
    """Coerce value to float."""
    if isinstance(value, bool):
        raise TypeError("Boolean is not a valid float")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        return float(value)
    raise TypeError(f"Cannot coerce {type(value).__name__} to float")


def _coerce_bool(value: Any) -> bool:
    """Coerce value to bool."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lower = value.lower()
        if lower in ("true", "1", "yes", "on"):
            return True
        if lower in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"Cannot interpret '{value}' as boolean")
    if isinstance(value, int):
        return bool(value)
    raise TypeError(f"Cannot coerce {type(value).__name__} to bool")


def _coerce_str(value: Any) -> str:
    """Coerce value to str."""
    if isinstance(value, str):
        return value
    return str(value)


def _coerce_uuid(value: Any) -> UUID:
    """Coerce value to UUID."""
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise TypeError(f"Cannot coerce {type(value).__name__} to UUID")


def _coerce_datetime(value: Any) -> datetime:
    """Coerce value to datetime."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise TypeError(f"Cannot coerce {type(value).__name__} to datetime")


def _coerce_date(value: Any) -> date:
    """Coerce value to date."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"Cannot coerce {type(value).__name__} to date")


# Type coercion registry
COERCERS: dict[type, Any] = {
    int: _coerce_int,
    float: _coerce_float,
    bool: _coerce_bool,
    str: _coerce_str,
    UUID: _coerce_uuid,
    datetime: _coerce_datetime,
    date: _coerce_date,
}


def coerce_value(value: Any, target_type: Any, *, _depth: int = 0) -> Any:
    """Coerce value to target type.

    Args:
        value: Value to coerce.
        target_type: Target type to coerce to.
        _depth: Internal recursion depth counter.

    Returns:
        Coerced value.

    Raises:
        TypeError: If coercion is not possible.
        RecursionError: If maximum recursion depth is exceeded.
    """
    # Check recursion depth to prevent circular reference DoS
    if _depth > _MAX_COERCION_DEPTH:
        raise RecursionError(
            f"Maximum schema nesting depth ({_MAX_COERCION_DEPTH}) exceeded. "
            "This may indicate a circular reference in your schema definitions."
        )

    origin = get_origin(target_type)
    args = get_args(target_type)

    # Handle Optional[T] (Union[T, None])
    if origin is Union:
        if value is None and type(None) in args:
            return None
        # Try non-None types
        for arg in args:
            if arg is not type(None):
                return coerce_value(value, arg, _depth=_depth + 1)

    # Handle list[T]
    if origin is list:
        if not isinstance(value, (list, tuple)):
            raise TypeError("Expected list")
        elem_type = args[0] if args else Any
        from pykour.schema.errors import ErrorDetail, ValidationError

        result = []
        elem_errors: list[ErrorDetail] = []
        for i, v in enumerate(value):
            try:
                result.append(coerce_value(v, elem_type, _depth=_depth + 1))
            except ValidationError as e:
                for err in e.errors:
                    # Insert array index after the first "body" element
                    new_loc: tuple[str | int, ...] = err.loc[:1] + (i,) + err.loc[1:]
                    elem_errors.append(
                        ErrorDetail(
                            loc=new_loc,
                            msg=err.msg,
                            type=err.type,
                            input=err.input,
                            ctx=err.ctx,
                        )
                    )
            except (TypeError, ValueError) as e:
                elem_errors.append(
                    ErrorDetail(
                        loc=("body", i),
                        msg=str(e),
                        type="type_error",
                        input=v,
                    )
                )
        if elem_errors:
            raise ValidationError(elem_errors)
        return result

    # Handle dict[K, V]
    if origin is dict:
        if not isinstance(value, dict):
            raise TypeError("Expected dict")
        key_type, val_type = args if len(args) == 2 else (Any, Any)
        return {
            coerce_value(k, key_type, _depth=_depth + 1): coerce_value(
                v, val_type, _depth=_depth + 1
            )
            for k, v in value.items()
        }

    # Direct type match
    if target_type is Any:
        return value

    # Special case: bool is subclass of int, but we don't want to treat bool as int
    if target_type is int and isinstance(value, bool):
        raise TypeError("Boolean is not a valid integer")

    if isinstance(value, target_type):
        return value

    # Use registered coercer
    if target_type in COERCERS:
        return COERCERS[target_type](value)

    # Check for Schema subclass (nested schema)
    if isinstance(target_type, type):
        # Import here to avoid circular import
        from pykour.schema.base import Schema

        if issubclass(target_type, Schema):
            if isinstance(value, dict):
                # Pass depth to nested schema creation
                return target_type._create_with_depth(value, _depth + 1)
            raise TypeError(
                f"Expected dict for nested Schema, got {type(value).__name__}"
            )

    raise TypeError(f"No coercer for {target_type}")
