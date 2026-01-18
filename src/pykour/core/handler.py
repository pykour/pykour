"""Request handling utilities for Pykour."""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime
from email.utils import format_datetime, parsedate_to_datetime
from typing import TYPE_CHECKING, Any

from pykour import json as pykour_json
from pykour.response import Response

if TYPE_CHECKING:
    pass

logger = logging.getLogger("pykour")

# Characters that are dangerous in HTTP headers (can cause response splitting)
_HEADER_UNSAFE_PATTERN = re.compile(r"[\r\n\x00]")

# Characters that are dangerous in cache keys (can cause cache poisoning)
_CACHE_KEY_UNSAFE_PATTERN = re.compile(r"[\r\n\x00:/\\]")


def _sanitize_header_value(value: str) -> str:
    """Remove characters that could cause HTTP header injection.

    Prevents HTTP response splitting attacks by removing CR, LF, and NUL bytes.

    Args:
        value: The raw value to sanitize.

    Returns:
        Sanitized value safe for use in HTTP headers.
    """
    return _HEADER_UNSAFE_PATTERN.sub("", value)


def _sanitize_cache_key(value: str) -> str:
    """Sanitize a value for safe use in cache keys.

    Removes characters that could cause cache key manipulation or confusion.

    Args:
        value: The raw value to sanitize.

    Returns:
        Sanitized value safe for use in cache keys.
    """
    return _CACHE_KEY_UNSAFE_PATTERN.sub("_", value)


def interpolate_cache_key(template: str, kwargs: dict[str, Any]) -> str:
    """Interpolate {param} placeholders in cache key template.

    Values are sanitized to prevent cache key manipulation attacks.

    Args:
        template: Key template with {param} placeholders.
        kwargs: Handler kwargs for interpolation.

    Returns:
        Interpolated cache key with sanitized values.

    Raises:
        ValueError: If a referenced parameter is not found in kwargs.

    Example:
        template = "user:{id}:profile"
        kwargs = {"id": 123, "request": ...}
        result = "user:123:profile"
    """

    def replace(match: re.Match[str]) -> str:
        param_name = match.group(1)
        if param_name in kwargs:
            # Sanitize value to prevent cache key manipulation
            return _sanitize_cache_key(str(kwargs[param_name]))
        raise ValueError(f"Cache key references unknown parameter: {param_name}")

    return re.sub(r"\{(\w+)\}", replace, template)


def interpolate_header_value(
    template: str,
    kwargs: dict[str, Any],
    response: Response,
) -> str | None:
    """Interpolate {param} placeholders in header value template.

    Values are sanitized to prevent HTTP header injection attacks.

    Args:
        template: Value template with {param} or {param.field} placeholders.
        kwargs: Handler kwargs for interpolation.
        response: Response object for response body interpolation.

    Returns:
        Interpolated value with sanitized values, or None if interpolation failed.

    Example:
        template = "/users/{id}"
        kwargs = {"id": 123}
        result = "/users/123"

        # With response body
        template = "/users/{id}"
        kwargs = {}
        response.body = b'{"id": 456}'
        result = "/users/456"
    """

    def get_value(param_path: str) -> str | None:
        """Get value for a parameter path (supports dot notation)."""
        parts = param_path.split(".")

        # First, try to resolve from kwargs
        if parts[0] in kwargs:
            value = kwargs[parts[0]]
            for part in parts[1:]:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None
            # Sanitize to prevent HTTP header injection
            return _sanitize_header_value(str(value))

        # Then, try to resolve from response body
        if hasattr(response, "body") and response.body:
            try:
                data = pykour_json.loads(response.body)
                for part in parts:
                    if isinstance(data, dict) and part in data:
                        data = data[part]
                    else:
                        return None
                # Sanitize to prevent HTTP header injection
                return _sanitize_header_value(str(data))
            except Exception:
                pass

        return None

    def replace(match: re.Match[str]) -> str:
        param_path = match.group(1)
        value = get_value(param_path)
        if value is not None:
            return value
        # If value not found, keep the original placeholder
        return match.group(0)

    result = re.sub(r"\{([^}]+)\}", replace, template)
    # Return None if any placeholder was not resolved
    if "{" in result:
        logger.warning(
            "Header value interpolation incomplete: unresolved placeholders in '%s' -> '%s'",
            template,
            result,
        )
        return None
    return result


def serialize_response(response: Response) -> bytes:
    """Serialize a Response object for caching.

    Args:
        response: Response to serialize.

    Returns:
        Serialized response as bytes.
    """
    data = {
        "status_code": response.status_code,
        "headers": response.headers,
        "body": response.body.decode("utf-8"),
        "media_type": response.media_type,
    }
    return pykour_json.dumps(data)


def deserialize_response(data: bytes) -> Response:
    """Deserialize cached bytes to a Response object.

    Args:
        data: Cached response bytes.

    Returns:
        Reconstructed Response object.
    """
    parsed = pykour_json.loads(data)
    return Response(
        content=parsed["body"],
        status_code=parsed["status_code"],
        headers=parsed["headers"],
        media_type=parsed.get("media_type"),
    )


# =============================================================================
# ETag / Last-Modified Helper Functions
# =============================================================================


def compute_etag(
    body: bytes,
    *,
    weak: bool = False,
    algorithm: str = "md5",
) -> str:
    """Compute ETag from response body.

    Args:
        body: Response body bytes.
        weak: Generate weak ETag (W/"...").
        algorithm: Hash algorithm ("md5", "sha1", "sha256").

    Returns:
        ETag string (e.g., '"abc123"' or 'W/"abc123"').

    Raises:
        ValueError: If unsupported algorithm is specified.
    """
    if algorithm == "md5":
        hash_obj = hashlib.md5(body, usedforsecurity=False)
    elif algorithm == "sha1":
        hash_obj = hashlib.sha1(body, usedforsecurity=False)
    elif algorithm == "sha256":
        hash_obj = hashlib.sha256(body)
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    hash_value = hash_obj.hexdigest()

    if weak:
        return f'W/"{hash_value}"'
    return f'"{hash_value}"'


def check_etag_match(if_none_match: str, etag: str) -> bool:
    """Check if If-None-Match header matches the ETag.

    Handles multiple ETags and wildcard (*).

    Args:
        if_none_match: If-None-Match header value.
        etag: Computed ETag value.

    Returns:
        True if any ETag matches.
    """
    if if_none_match.strip() == "*":
        return True

    def normalize(tag: str) -> str:
        """Normalize ETag for comparison (remove W/ prefix and quotes)."""
        tag = tag.strip()
        if tag.startswith("W/"):
            tag = tag[2:]
        return tag.strip('"')

    normalized_etag = normalize(etag)

    for tag in if_none_match.split(","):
        if normalize(tag) == normalized_etag:
            return True

    return False


def parse_if_modified_since(header_value: str) -> datetime | None:
    """Parse If-Modified-Since header value.

    Args:
        header_value: HTTP date string.

    Returns:
        Parsed datetime or None if parsing fails.
    """
    try:
        return parsedate_to_datetime(header_value)
    except (ValueError, TypeError):
        return None


def format_last_modified(dt: datetime) -> str:
    """Format datetime for Last-Modified header.

    Args:
        dt: Datetime to format.

    Returns:
        HTTP date string (RFC 7231 format).
    """
    return format_datetime(dt, usegmt=True)


def extract_last_modified(
    response: Response,
    static_value: datetime | None,
    response_field: str | None,
    date_format: str,
) -> datetime | None:
    """Extract Last-Modified timestamp from response or static value.

    Args:
        response: Response object.
        static_value: Fixed datetime value (highest priority).
        response_field: Field name to extract from response body.
        date_format: Format string for parsing field value.

    Returns:
        Extracted datetime or None.
    """
    if static_value is not None:
        return static_value

    if response_field is None:
        return None

    try:
        data = pykour_json.loads(response.body)

        # Support dot notation (e.g., "metadata.updated_at")
        parts = response_field.split(".")
        for part in parts:
            if isinstance(data, dict) and part in data:
                data = data[part]
            else:
                return None

        if isinstance(data, str):
            # Try ISO format first
            try:
                return datetime.fromisoformat(data.replace("Z", "+00:00"))
            except ValueError:
                pass
            # Try custom format
            return datetime.strptime(data, date_format)
        elif isinstance(data, int | float):
            # Unix timestamp
            return datetime.fromtimestamp(data)

    except Exception:
        pass

    return None
