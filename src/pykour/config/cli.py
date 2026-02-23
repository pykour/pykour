"""CLI-specific configuration utilities for Pykour.

This module provides functions for loading configuration in CLI contexts
(migrations, etc.) with a consistent priority order:

1. CLI flags (--database, etc.) - highest priority
2. Environment variables (PYKOUR_DATABASE_URL, etc.)
3. pykour.toml (with ${VAR} expansion)
4. Default values - lowest priority
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from pykour.config.loader import load_config

if TYPE_CHECKING:
    import argparse

    from pykour.config.models import PykourConfig


def get_cli_config() -> PykourConfig:
    """Load configuration for CLI commands.

    This loads the configuration from pykour.toml (if found) with
    environment variable expansion and overrides applied.

    Returns:
        PykourConfig instance
    """
    return load_config(auto_discover=True)


def get_database_url_from_config(
    args: argparse.Namespace | None = None,
    config: PykourConfig | None = None,
) -> str | None:
    """Get database URL following the priority order.

    Priority (highest to lowest):
    1. CLI flag (args.database)
    2. Environment variable (PYKOUR_DATABASE_URL)
    3. pykour.toml database.url (with ${VAR} expansion applied)

    Args:
        args: Parsed CLI arguments (optional)
        config: Pre-loaded PykourConfig (optional, will load if not provided)

    Returns:
        Database URL string, or None if not configured
    """
    # Priority 1: CLI flag
    if args is not None and hasattr(args, "database") and args.database:
        return args.database

    # Priority 2: Environment variable
    env_url = os.environ.get("PYKOUR_DATABASE_URL")
    if env_url:
        return env_url

    # Priority 3: pykour.toml (with ${VAR} expansion already applied)
    if config is None:
        config = get_cli_config()

    if config.database and config.database.url:
        return config.database.url

    return None


def get_config_value(
    key: str,
    args: Any = None,
    args_attr: str | None = None,
    env_var: str | None = None,
    config: PykourConfig | None = None,
    config_getter: Any = None,
    default: Any = None,
) -> Any:
    """Get a configuration value following the standard priority order.

    Priority (highest to lowest):
    1. CLI flag (args.{args_attr})
    2. Environment variable ({env_var})
    3. pykour.toml (via config_getter)
    4. Default value

    Args:
        key: Name of the configuration (for documentation)
        args: Parsed CLI arguments (optional)
        args_attr: Attribute name on args to check
        env_var: Environment variable name to check
        config: Pre-loaded PykourConfig (optional)
        config_getter: Callable that takes config and returns the value
        default: Default value if not found

    Returns:
        Configuration value
    """
    # Priority 1: CLI flag
    if args is not None and args_attr is not None:
        value = getattr(args, args_attr, None)
        if value is not None:
            return value

    # Priority 2: Environment variable
    if env_var is not None:
        env_value = os.environ.get(env_var)
        if env_value is not None:
            return env_value

    # Priority 3: pykour.toml
    if config_getter is not None:
        if config is None:
            config = get_cli_config()
        try:
            config_value = config_getter(config)
            if config_value is not None:
                return config_value
        except (AttributeError, KeyError):
            pass

    return default
