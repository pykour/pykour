"""Tests for pykour.core.handler module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pykour.core.handler import (
    _sanitize_cache_key,
    _sanitize_header_value,
    check_etag_match,
    compute_etag,
    deserialize_response,
    extract_last_modified,
    format_last_modified,
    interpolate_cache_key,
    interpolate_header_value,
    parse_if_modified_since,
    serialize_response,
)
from pykour.response import Response


class TestSanitizeHeaderValue:
    """Tests for _sanitize_header_value function."""

    def test_removes_carriage_return(self) -> None:
        """Should remove carriage return characters."""
        assert _sanitize_header_value("hello\rworld") == "helloworld"

    def test_removes_newline(self) -> None:
        """Should remove newline characters."""
        assert _sanitize_header_value("hello\nworld") == "helloworld"

    def test_removes_null_byte(self) -> None:
        """Should remove null byte characters."""
        assert _sanitize_header_value("hello\x00world") == "helloworld"

    def test_removes_crlf_sequence(self) -> None:
        """Should remove CRLF injection attempts."""
        assert (
            _sanitize_header_value("value\r\nX-Injected: header")
            == "valueX-Injected: header"
        )

    def test_preserves_safe_characters(self) -> None:
        """Should preserve normal characters."""
        safe_value = "application/json; charset=utf-8"
        assert _sanitize_header_value(safe_value) == safe_value

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert _sanitize_header_value("") == ""


class TestSanitizeCacheKey:
    """Tests for _sanitize_cache_key function."""

    def test_removes_carriage_return(self) -> None:
        """Should replace carriage return with underscore."""
        assert _sanitize_cache_key("key\rvalue") == "key_value"

    def test_removes_newline(self) -> None:
        """Should replace newline with underscore."""
        assert _sanitize_cache_key("key\nvalue") == "key_value"

    def test_removes_null_byte(self) -> None:
        """Should replace null byte with underscore."""
        assert _sanitize_cache_key("key\x00value") == "key_value"

    def test_removes_colon(self) -> None:
        """Should replace colon with underscore."""
        assert _sanitize_cache_key("key:value:suffix") == "key_value_suffix"

    def test_removes_forward_slash(self) -> None:
        """Should replace forward slash with underscore."""
        assert _sanitize_cache_key("path/to/key") == "path_to_key"

    def test_removes_backslash(self) -> None:
        """Should replace backslash with underscore."""
        assert _sanitize_cache_key("path\\to\\key") == "path_to_key"

    def test_preserves_safe_characters(self) -> None:
        """Should preserve alphanumeric and safe characters."""
        safe_value = "user_123_profile"
        assert _sanitize_cache_key(safe_value) == safe_value

    def test_empty_string(self) -> None:
        """Should handle empty string."""
        assert _sanitize_cache_key("") == ""


class TestInterpolateCacheKey:
    """Tests for interpolate_cache_key function."""

    def test_single_placeholder(self) -> None:
        """Should interpolate single placeholder."""
        result = interpolate_cache_key("user:{id}:profile", {"id": 123})
        assert result == "user:123:profile"

    def test_multiple_placeholders(self) -> None:
        """Should interpolate multiple placeholders."""
        result = interpolate_cache_key(
            "user:{user_id}:item:{item_id}",
            {"user_id": 1, "item_id": 42},
        )
        assert result == "user:1:item:42"

    def test_sanitizes_values(self) -> None:
        """Should sanitize interpolated values."""
        result = interpolate_cache_key("key:{value}", {"value": "mal:icious"})
        assert result == "key:mal_icious"

    def test_no_placeholders(self) -> None:
        """Should return template as-is if no placeholders."""
        result = interpolate_cache_key("static:key", {})
        assert result == "static:key"

    def test_missing_parameter_raises_error(self) -> None:
        """Should raise ValueError for missing parameter."""
        with pytest.raises(ValueError, match="unknown parameter"):
            interpolate_cache_key("user:{id}", {"other": 123})

    def test_string_value(self) -> None:
        """Should handle string values."""
        result = interpolate_cache_key("user:{name}", {"name": "alice"})
        assert result == "user:alice"


class TestInterpolateHeaderValue:
    """Tests for interpolate_header_value function."""

    def test_single_placeholder(self) -> None:
        """Should interpolate single placeholder from kwargs."""
        response = Response(content="")
        result = interpolate_header_value("/users/{id}", {"id": 123}, response)
        assert result == "/users/123"

    def test_nested_dict_access(self) -> None:
        """Should support dot notation for nested dicts."""
        response = Response(content="")
        kwargs = {"user": {"id": 456}}
        result = interpolate_header_value("/users/{user.id}", kwargs, response)
        assert result == "/users/456"

    def test_interpolate_from_response_body(self) -> None:
        """Should interpolate from JSON response body when not in kwargs."""
        response = Response(content='{"id": 789, "name": "test"}')
        result = interpolate_header_value("/users/{id}", {}, response)
        assert result == "/users/789"

    def test_nested_response_body(self) -> None:
        """Should support dot notation for response body."""
        response = Response(content='{"data": {"id": 999}}')
        result = interpolate_header_value("/items/{data.id}", {}, response)
        assert result == "/items/999"

    def test_sanitizes_header_values(self) -> None:
        """Should sanitize interpolated values for header safety."""
        response = Response(content="")
        result = interpolate_header_value(
            "value: {param}",
            {"param": "evil\r\nX-Injected: header"},
            response,
        )
        assert result == "value: evilX-Injected: header"

    def test_unresolved_placeholder_returns_none(self) -> None:
        """Should return None if placeholder cannot be resolved."""
        response = Response(content="")
        result = interpolate_header_value("/users/{unknown}", {}, response)
        assert result is None

    def test_no_placeholders(self) -> None:
        """Should return template as-is if no placeholders."""
        response = Response(content="")
        result = interpolate_header_value("static-value", {}, response)
        assert result == "static-value"


class TestSerializeDeserializeResponse:
    """Tests for serialize_response and deserialize_response functions."""

    def test_serialize_basic_response(self) -> None:
        """Should serialize basic response to bytes."""
        response = Response(content="Hello", status_code=200)
        serialized = serialize_response(response)
        assert isinstance(serialized, bytes)
        assert b"Hello" in serialized
        assert b"200" in serialized

    def test_deserialize_basic_response(self) -> None:
        """Should deserialize bytes back to Response."""
        response = Response(
            content="Test content",
            status_code=201,
            headers={"X-Custom": "value"},
        )
        serialized = serialize_response(response)
        restored = deserialize_response(serialized)

        assert restored.status_code == 201
        assert restored.body == b"Test content"
        # Headers may be stored as list of tuples or dict
        if isinstance(restored.headers, dict):
            assert restored.headers.get("X-Custom") == "value"
        else:
            header_dict = dict(restored.headers)
            assert header_dict.get("X-Custom") == "value"

    def test_roundtrip_preserves_data(self) -> None:
        """Should preserve all response data through serialization roundtrip."""
        response = Response(
            content='{"key": "value"}',
            status_code=200,
            headers={"Content-Type": "application/json"},
            media_type="application/json",
        )
        restored = deserialize_response(serialize_response(response))

        assert restored.status_code == response.status_code
        assert restored.body == response.body
        assert restored.media_type == response.media_type


class TestComputeEtag:
    """Tests for compute_etag function."""

    def test_md5_etag(self) -> None:
        """Should compute MD5 ETag."""
        body = b"test content"
        etag = compute_etag(body, algorithm="md5")
        assert etag.startswith('"')
        assert etag.endswith('"')
        assert len(etag) == 34  # 32 hex chars + 2 quotes

    def test_sha1_etag(self) -> None:
        """Should compute SHA1 ETag."""
        body = b"test content"
        etag = compute_etag(body, algorithm="sha1")
        assert len(etag) == 42  # 40 hex chars + 2 quotes

    def test_sha256_etag(self) -> None:
        """Should compute SHA256 ETag."""
        body = b"test content"
        etag = compute_etag(body, algorithm="sha256")
        assert len(etag) == 66  # 64 hex chars + 2 quotes

    def test_weak_etag(self) -> None:
        """Should generate weak ETag with W/ prefix."""
        body = b"test content"
        etag = compute_etag(body, weak=True)
        assert etag.startswith('W/"')
        assert etag.endswith('"')

    def test_same_content_same_etag(self) -> None:
        """Should produce same ETag for same content."""
        body = b"consistent content"
        assert compute_etag(body) == compute_etag(body)

    def test_different_content_different_etag(self) -> None:
        """Should produce different ETag for different content."""
        assert compute_etag(b"content A") != compute_etag(b"content B")

    def test_unsupported_algorithm_raises_error(self) -> None:
        """Should raise ValueError for unsupported algorithm."""
        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            compute_etag(b"test", algorithm="sha512")


class TestCheckEtagMatch:
    """Tests for check_etag_match function."""

    def test_exact_match(self) -> None:
        """Should match exact ETag."""
        assert check_etag_match('"abc123"', '"abc123"') is True

    def test_wildcard_match(self) -> None:
        """Should match wildcard."""
        assert check_etag_match("*", '"any-etag"') is True

    def test_weak_etag_match(self) -> None:
        """Should match weak ETag against strong."""
        assert check_etag_match('W/"abc123"', '"abc123"') is True

    def test_multiple_etags_match(self) -> None:
        """Should match one of multiple ETags."""
        assert check_etag_match('"other", "match", "another"', '"match"') is True

    def test_no_match(self) -> None:
        """Should not match different ETag."""
        assert check_etag_match('"abc"', '"xyz"') is False

    def test_whitespace_handling(self) -> None:
        """Should handle whitespace around ETags."""
        assert check_etag_match('  "abc123"  ', '"abc123"') is True


class TestParseIfModifiedSince:
    """Tests for parse_if_modified_since function."""

    def test_parse_valid_date(self) -> None:
        """Should parse valid HTTP date."""
        result = parse_if_modified_since("Sun, 06 Nov 1994 08:49:37 GMT")
        assert result is not None
        assert result.year == 1994
        assert result.month == 11
        assert result.day == 6

    def test_invalid_date_returns_none(self) -> None:
        """Should return None for invalid date."""
        result = parse_if_modified_since("invalid-date")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        """Should return None for empty string."""
        result = parse_if_modified_since("")
        assert result is None


class TestFormatLastModified:
    """Tests for format_last_modified function."""

    def test_format_datetime(self) -> None:
        """Should format datetime in HTTP date format."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = format_last_modified(dt)
        assert "15 Jan 2024" in result or "Mon, 15 Jan 2024" in result
        assert "GMT" in result


class TestExtractLastModified:
    """Tests for extract_last_modified function."""

    def test_static_value_priority(self) -> None:
        """Should use static value when provided."""
        static = datetime(2024, 1, 1, tzinfo=timezone.utc)
        response = Response(content='{"updated": "2025-01-01"}')
        result = extract_last_modified(response, static, "updated", "%Y-%m-%d")
        assert result == static

    def test_extract_from_response_iso_format(self) -> None:
        """Should extract ISO format datetime from response."""
        response = Response(content='{"updated_at": "2024-06-15T14:30:00+00:00"}')
        result = extract_last_modified(response, None, "updated_at", "%Y-%m-%d")
        assert result is not None
        assert result.year == 2024
        assert result.month == 6
        assert result.day == 15

    def test_extract_from_nested_field(self) -> None:
        """Should extract from nested field using dot notation."""
        response = Response(content='{"meta": {"last_update": "2024-03-20T00:00:00Z"}}')
        result = extract_last_modified(response, None, "meta.last_update", "%Y-%m-%d")
        assert result is not None
        assert result.year == 2024
        assert result.month == 3

    def test_extract_unix_timestamp(self) -> None:
        """Should extract unix timestamp."""
        response = Response(content='{"timestamp": 1704067200}')  # 2024-01-01
        result = extract_last_modified(response, None, "timestamp", "%Y-%m-%d")
        assert result is not None
        assert result.year == 2024

    def test_missing_field_returns_none(self) -> None:
        """Should return None for missing field."""
        response = Response(content='{"other": "value"}')
        result = extract_last_modified(response, None, "updated_at", "%Y-%m-%d")
        assert result is None

    def test_no_response_field_returns_none(self) -> None:
        """Should return None when response_field is None."""
        response = Response(content='{"updated_at": "2024-01-01"}')
        result = extract_last_modified(response, None, None, "%Y-%m-%d")
        assert result is None

    def test_invalid_json_returns_none(self) -> None:
        """Should return None for invalid JSON."""
        response = Response(content="not json")
        result = extract_last_modified(response, None, "field", "%Y-%m-%d")
        assert result is None
