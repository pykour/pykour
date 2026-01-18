"""Environment variable processing for Pykour configuration."""

import os
from typing import Any, Callable

from pykour.config.models import PykourConfig


def _str_to_bool(value: str) -> bool:
    """Convert string to boolean."""
    return value.lower() in ("1", "true", "yes")


# Environment variable mappings: (env_name, config_path, converter)
# config_path is a tuple of attribute names to traverse
ENV_MAPPINGS: list[tuple[str, tuple[str, ...], Callable[[str], Any]]] = [
    ("PYKOUR_DEBUG", ("app", "debug"), _str_to_bool),
    ("PYKOUR_ROUTES_DIR", ("app", "routes_dir"), str),
    ("PYKOUR_DATABASE_URL", ("database", "url"), str),
    ("PYKOUR_CACHE_URL", ("cache", "url"), str),
    ("PYKOUR_LOG_LEVEL", ("logging", "level"), str),
    ("PYKOUR_LOG_FORMAT", ("logging", "format"), str),
    ("PYKOUR_JWT_SECRET_KEY", ("middleware", "jwt", "secret_key"), str),
]


def _set_nested_attr(obj: Any, path: tuple[str, ...], value: Any) -> None:
    """Set a nested attribute on an object.

    Args:
        obj: The root object
        path: Tuple of attribute names to traverse
        value: The value to set
    """
    for attr in path[:-1]:
        obj = getattr(obj, attr)
    setattr(obj, path[-1], value)


def apply_env_overrides(config: PykourConfig) -> PykourConfig:
    """Apply environment variable overrides to configuration.

    Environment variables take precedence over config file values.

    Args:
        config: The configuration object to modify

    Returns:
        The modified configuration object
    """
    for env_name, config_path, converter in ENV_MAPPINGS:
        value = os.environ.get(env_name)
        if value is not None:
            converted_value = converter(value)
            _set_nested_attr(config, config_path, converted_value)

    return config
