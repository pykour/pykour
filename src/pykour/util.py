import logging
from typing import Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger("pykour")


def cast(value: Any, to_type: type) -> Any:
    try:
        if to_type == int:
            return int(value)
        if to_type == float:
            return float(value)
        if to_type == bool:
            return value.lower() in ["true", "1", "yes"]
        if to_type == datetime:
            return datetime.strptime(value, "%Y-%m-%d")
        if issubclass(to_type, Enum):
            try:
                return to_type[value]
            except KeyError:
                raise ValueError(f"{value} is not a valid {to_type.__name__}")
        return value
    except Exception as e:
        if logger.isEnabledFor(logging.ERROR):
            logger.error(f"Error casting value '{value}' to type '{to_type}': {e}")
        raise e
