from typing import Callable, Any


def validate(field_name: str) -> Callable:
    """Validator decorator.

    Args:
        field_name: The name of the field to validate.
    """

    def decorator(func: Callable[[Any], None]) -> Callable[[Any], None]:
        func.__validator__ = field_name  # type: ignore[attr-defined]
        return func

    return decorator
