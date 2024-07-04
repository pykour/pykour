from typing import Callable, Any


def validate(field_name: str) -> Callable:
    def decorator(func: Callable[[Any], None]) -> Callable[[Any], None]:
        func.__validator__ = field_name
        return func

    return decorator
