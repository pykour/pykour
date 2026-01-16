"""Common utilities for Pykour middleware.

This module provides shared functionality across middleware components
to reduce code duplication and ensure consistency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from pykour.types import Scope

# Sensitive headers that should be masked in logs
SENSITIVE_HEADERS = frozenset(
    {
        # Authentication headers
        "authorization",
        "proxy-authorization",
        "www-authenticate",
        "proxy-authenticate",
        # Cookie headers
        "cookie",
        "set-cookie",
        # API key headers
        "x-api-key",
        "api-key",
        "x-auth-token",
        "x-access-token",
        # Custom token headers
        "token",
        "bearer",
        "secret",
        "password",
        # CSRF tokens
        "x-csrf-token",
        "x-xsrf-token",
        # Session headers
        "session-id",
        "x-session-id",
    }
)


def is_path_excluded(
    path: str,
    exclude_paths: Sequence[str],
    *,
    match_prefix: bool = True,
) -> bool:
    """Check if a path matches any exclusion pattern.

    Args:
        path: The request path to check.
        exclude_paths: List of paths/prefixes to exclude.
        match_prefix: If True, also match paths that start with
            an excluded path followed by "/".

    Returns:
        True if the path is excluded, False otherwise.

    Examples:
        >>> is_path_excluded("/health", ["/health", "/metrics"])
        True
        >>> is_path_excluded("/health/check", ["/health"])
        True
        >>> is_path_excluded("/api/health", ["/health"])
        False
        >>> is_path_excluded("/health", ["/health"], match_prefix=False)
        True
        >>> is_path_excluded("/health/check", ["/health"], match_prefix=False)
        False
    """
    for excluded in exclude_paths:
        if path == excluded:
            return True
        if match_prefix and path.startswith(excluded + "/"):
            return True
    return False


def extract_header(
    scope: "Scope",
    header_name: bytes | str,
    *,
    default: str | None = None,
) -> str | None:
    """Extract a single header value from ASGI scope.

    Args:
        scope: ASGI scope dictionary.
        header_name: Header name (as bytes or string).
        default: Default value if header not found.

    Returns:
        Header value as string, or default if not found.

    Examples:
        >>> scope = {"headers": [(b"content-type", b"application/json")]}
        >>> extract_header(scope, b"content-type")
        'application/json'
        >>> extract_header(scope, "content-type")
        'application/json'
        >>> extract_header(scope, b"x-custom", default="none")
        'none'
    """
    if isinstance(header_name, str):
        header_name = header_name.lower().encode("latin-1")
    else:
        header_name = header_name.lower()

    for key, value in scope.get("headers", []):
        if key.lower() == header_name:
            return value.decode("latin-1")
    return default


def extract_headers_dict(
    scope: "Scope",
    *,
    lowercase_keys: bool = True,
) -> dict[str, str]:
    """Extract all headers from ASGI scope as a dictionary.

    Args:
        scope: ASGI scope dictionary.
        lowercase_keys: If True, convert all header names to lowercase.

    Returns:
        Dictionary mapping header names to values.

    Note:
        If a header appears multiple times, only the last value is kept.

    Examples:
        >>> scope = {"headers": [(b"Content-Type", b"text/plain")]}
        >>> extract_headers_dict(scope)
        {'content-type': 'text/plain'}
    """
    headers = {}
    for key, value in scope.get("headers", []):
        key_str = key.decode("latin-1")
        if lowercase_keys:
            key_str = key_str.lower()
        headers[key_str] = value.decode("latin-1")
    return headers


def mask_sensitive_headers(
    headers: list[tuple[bytes, bytes]],
    *,
    mask_value: str = "[REDACTED]",
    additional_sensitive: set[str] | None = None,
) -> list[tuple[str, str]]:
    """Format headers with sensitive values masked.

    Args:
        headers: List of header tuples (name, value) as bytes.
        mask_value: String to use for masking sensitive values.
        additional_sensitive: Additional header names to mask.

    Returns:
        List of header tuples (name, value) as strings,
        with sensitive values replaced by mask_value.

    Examples:
        >>> headers = [(b"Authorization", b"Bearer token123")]
        >>> mask_sensitive_headers(headers)
        [('Authorization', '[REDACTED]')]
    """
    sensitive = SENSITIVE_HEADERS
    if additional_sensitive:
        sensitive = sensitive | additional_sensitive

    result = []
    for key, value in headers:
        key_str = key.decode("latin-1")
        if key_str.lower() in sensitive:
            result.append((key_str, mask_value))
        else:
            result.append((key_str, value.decode("latin-1")))
    return result


def format_headers_string(
    headers: list[tuple[bytes, bytes]],
    *,
    separator: str = ", ",
    mask_sensitive: bool = True,
) -> str:
    """Format headers as a string for logging.

    Args:
        headers: List of header tuples (name, value) as bytes.
        separator: String to join header entries.
        mask_sensitive: If True, mask sensitive header values.

    Returns:
        Formatted string of headers.

    Examples:
        >>> headers = [(b"Content-Type", b"text/plain")]
        >>> format_headers_string(headers)
        'Content-Type: text/plain'
    """
    if mask_sensitive:
        formatted_headers = mask_sensitive_headers(headers)
    else:
        formatted_headers = [
            (k.decode("latin-1"), v.decode("latin-1")) for k, v in headers
        ]

    return separator.join(f"{k}: {v}" for k, v in formatted_headers)


def get_client_ip(scope: "Scope") -> str:
    """Extract client IP address from ASGI scope.

    Checks X-Forwarded-For header first for reverse proxy support,
    then falls back to the client tuple.

    Args:
        scope: ASGI scope dictionary.

    Returns:
        Client IP address string, or "-" if not found.

    Examples:
        >>> scope = {"client": ("192.168.1.1", 8080)}
        >>> get_client_ip(scope)
        '192.168.1.1'
    """
    # Check X-Forwarded-For header first (for reverse proxies)
    x_forwarded_for = extract_header(scope, b"x-forwarded-for")
    if x_forwarded_for:
        # Take the first IP in the chain (original client)
        return x_forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header
    x_real_ip = extract_header(scope, b"x-real-ip")
    if x_real_ip:
        return x_real_ip.strip()

    # Fall back to client tuple
    client = scope.get("client")
    if client:
        return client[0]
    return "-"


def get_user_agent(scope: "Scope") -> str:
    """Extract User-Agent header from ASGI scope.

    Args:
        scope: ASGI scope dictionary.

    Returns:
        User-Agent string, or "-" if not found.
    """
    return extract_header(scope, b"user-agent", default="-") or "-"


def get_content_length(scope: "Scope") -> int:
    """Extract Content-Length from request headers.

    Args:
        scope: ASGI scope dictionary.

    Returns:
        Content length as integer, or 0 if not present or invalid.
    """
    content_length = extract_header(scope, b"content-length")
    if content_length:
        try:
            return int(content_length)
        except ValueError:
            pass
    return 0


def extract_bearer_token(scope: "Scope") -> str | None:
    """Extract Bearer token from Authorization header.

    The scheme comparison is case-insensitive per RFC 7235.

    Args:
        scope: ASGI scope dictionary.

    Returns:
        Token string if found, None otherwise.

    Examples:
        >>> scope = {"headers": [(b"authorization", b"Bearer abc123")]}
        >>> extract_bearer_token(scope)
        'abc123'
        >>> scope = {"headers": [(b"authorization", b"bearer abc123")]}
        >>> extract_bearer_token(scope)
        'abc123'
        >>> scope = {"headers": [(b"authorization", b"BEARER abc123")]}
        >>> extract_bearer_token(scope)
        'abc123'
        >>> scope = {"headers": [(b"authorization", b"Basic xyz")]}
        >>> extract_bearer_token(scope) is None
        True
    """
    auth = extract_header(scope, b"authorization")
    if not auth:
        return None

    # Split on whitespace and validate format
    parts = auth.strip().split(None, 1)
    if len(parts) != 2:
        return None

    scheme, token = parts
    if scheme.lower() != "bearer":
        return None

    return token.strip() if token.strip() else None
