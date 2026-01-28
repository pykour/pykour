"""Log message sanitizer for sensitive information masking.

This module provides utilities to mask sensitive information in log messages,
such as passwords, API keys, tokens, and other credentials.

Example:
    from pykour.logging.sanitizer import sanitize_log_message

    message = 'User login with password="secret123"'
    safe_message = sanitize_log_message(message)
    # Output: 'User login with password="***"'
"""

from __future__ import annotations

import re
from typing import Any, Pattern

# Sensitive field patterns to mask
# Each pattern captures the value portion to be replaced
SENSITIVE_PATTERNS: list[tuple[Pattern[str], str]] = [
    # password="value" or password: value or password=value
    (
        re.compile(
            r'(password["\']?\s*[:=]\s*["\']?)([^"\'\s,}\]]+)(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***\3",
    ),
    # token="value" or token: value
    (
        re.compile(
            r'(token["\']?\s*[:=]\s*["\']?)([^"\'\s,}\]]+)(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***\3",
    ),
    # api_key="value" or api-key="value" or apikey="value"
    (
        re.compile(
            r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'\s,}\]]+)(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***\3",
    ),
    # secret="value" or secret_key="value"
    (
        re.compile(
            r'(secret[_]?[a-z]*["\']?\s*[:=]\s*["\']?)([^"\'\s,}\]]+)(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***\3",
    ),
    # authorization="value" or Authorization: Bearer xxx
    (
        re.compile(
            r'(authorization["\']?\s*[:=]\s*["\']?)([^"\'\s,}\]]+)(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***\3",
    ),
    # Bearer token in headers
    (
        re.compile(r"(Bearer\s+)([A-Za-z0-9\-._~+/]+=*)", re.IGNORECASE),
        r"\1***",
    ),
    # Basic auth credentials
    (
        re.compile(r"(Basic\s+)([A-Za-z0-9+/]+=*)", re.IGNORECASE),
        r"\1***",
    ),
    # credential="value"
    (
        re.compile(
            r'(credential[s]?["\']?\s*[:=]\s*["\']?)([^"\'\s,}\]]+)(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***\3",
    ),
    # private_key="value" or privatekey="value"
    (
        re.compile(
            r'(private[_]?key["\']?\s*[:=]\s*["\']?)([^"\'\s,}\]]+)(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***\3",
    ),
    # access_token="value"
    (
        re.compile(
            r'(access[_]?token["\']?\s*[:=]\s*["\']?)([^"\'\s,}\]]+)(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***\3",
    ),
    # refresh_token="value"
    (
        re.compile(
            r'(refresh[_]?token["\']?\s*[:=]\s*["\']?)([^"\'\s,}\]]+)(["\']?)',
            re.IGNORECASE,
        ),
        r"\1***\3",
    ),
]


def sanitize_log_message(message: str) -> str:
    """Sanitize a log message by masking sensitive information.

    This function replaces sensitive values like passwords, API keys,
    tokens, and other credentials with '***' to prevent them from
    appearing in log files.

    Args:
        message: The log message to sanitize.

    Returns:
        The sanitized message with sensitive values masked.

    Example:
        >>> sanitize_log_message('password="secret123"')
        'password="***"'
        >>> sanitize_log_message('Authorization: Bearer eyJhbGc...')
        'Authorization: Bearer ***'
        >>> sanitize_log_message('api_key=abc123&user=john')
        'api_key=***&user=john'
    """
    result = message
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize a dictionary by masking sensitive values.

    This function recursively processes a dictionary and masks values
    for keys that match sensitive field names.

    Args:
        data: The dictionary to sanitize.

    Returns:
        A new dictionary with sensitive values masked.

    Example:
        >>> sanitize_dict({"password": "secret", "user": "john"})
        {'password': '***', 'user': 'john'}
    """
    sensitive_keys = {
        "password",
        "token",
        "api_key",
        "apikey",
        "api-key",
        "secret",
        "secret_key",
        "authorization",
        "credential",
        "credentials",
        "private_key",
        "privatekey",
        "access_token",
        "refresh_token",
    }

    result: dict[str, Any] = {}
    for key, value in data.items():
        key_lower = key.lower()
        if key_lower in sensitive_keys:
            result[key] = "***"
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result
