"""Tests for conditional request decorators (ETag, Last-Modified)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pykour import JSONResponse, Pykour, Request
from pykour.cache import InMemoryStorage
from pykour.cache.decorators import cache
from pykour.conditional import (
    ETAG_REGISTRY_ATTR,
    etag,
    get_etag_info,
    get_last_modified_info,
    last_modified,
)
from pykour.core.handler import (
    check_etag_match,
    compute_etag,
    extract_last_modified,
    format_last_modified,
    parse_if_modified_since,
)
from pykour.response import Response
from pykour.testing import TestClient


# =============================================================================
# Unit Tests for Decorators
# =============================================================================


class TestETagDecorator:
    """Tests for @etag decorator."""

    def test_etag_decorator_adds_metadata(self) -> None:
        """Test that @etag adds ETagInfo metadata."""

        @etag()
        async def handler() -> dict[str, str]:
            return {}

        assert hasattr(handler, ETAG_REGISTRY_ATTR)
        infos = get_etag_info(handler)
        assert len(infos) == 1
        assert infos[0].weak is False
        assert infos[0].algorithm == "md5"

    def test_etag_decorator_with_weak(self) -> None:
        """Test @etag with weak option."""

        @etag(weak=True)
        async def handler() -> dict[str, str]:
            return {}

        infos = get_etag_info(handler)
        assert infos[0].weak is True

    def test_etag_decorator_with_algorithm(self) -> None:
        """Test @etag with custom algorithm."""

        @etag(algorithm="sha256")
        async def handler() -> dict[str, str]:
            return {}

        infos = get_etag_info(handler)
        assert infos[0].algorithm == "sha256"

    def test_get_etag_info_no_decorator(self) -> None:
        """Test get_etag_info returns empty list for plain function."""

        async def plain_func() -> dict[str, str]:
            return {}

        assert get_etag_info(plain_func) == []


class TestLastModifiedDecorator:
    """Tests for @last_modified decorator."""

    def test_last_modified_with_static_value(self) -> None:
        """Test @last_modified with static datetime value."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0)

        @last_modified(value=fixed_time)
        async def handler() -> dict[str, str]:
            return {}

        infos = get_last_modified_info(handler)
        assert len(infos) == 1
        assert infos[0].static_value == fixed_time
        assert infos[0].response_field is None

    def test_last_modified_with_field(self) -> None:
        """Test @last_modified with response field."""

        @last_modified(field="updated_at")
        async def handler() -> dict[str, str]:
            return {}

        infos = get_last_modified_info(handler)
        assert infos[0].static_value is None
        assert infos[0].response_field == "updated_at"

    def test_last_modified_with_nested_field(self) -> None:
        """Test @last_modified with nested field (dot notation)."""

        @last_modified(field="metadata.modified_at")
        async def handler() -> dict[str, str]:
            return {}

        infos = get_last_modified_info(handler)
        assert infos[0].response_field == "metadata.modified_at"

    def test_get_last_modified_info_no_decorator(self) -> None:
        """Test get_last_modified_info returns empty list for plain function."""

        async def plain_func() -> dict[str, str]:
            return {}

        assert get_last_modified_info(plain_func) == []


# =============================================================================
# Unit Tests for Helper Functions
# =============================================================================


class TestComputeETag:
    """Tests for compute_etag function."""

    def test_compute_etag_md5(self) -> None:
        """Test ETag computation with MD5."""
        body = b'{"id": 1}'
        etag_value = compute_etag(body, algorithm="md5")

        assert etag_value.startswith('"')
        assert etag_value.endswith('"')
        assert len(etag_value) == 34  # 32 hex chars + 2 quotes

    def test_compute_etag_sha256(self) -> None:
        """Test ETag computation with SHA-256."""
        body = b'{"id": 1}'
        etag_value = compute_etag(body, algorithm="sha256")

        assert etag_value.startswith('"')
        assert etag_value.endswith('"')
        assert len(etag_value) == 66  # 64 hex chars + 2 quotes

    def test_compute_etag_weak(self) -> None:
        """Test weak ETag computation."""
        body = b'{"id": 1}'
        etag_value = compute_etag(body, weak=True)

        assert etag_value.startswith('W/"')
        assert etag_value.endswith('"')

    def test_compute_etag_unsupported_algorithm(self) -> None:
        """Test that unsupported algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            compute_etag(b"test", algorithm="unsupported")

    def test_compute_etag_deterministic(self) -> None:
        """Test that same body produces same ETag."""
        body = b'{"data": "test"}'
        etag1 = compute_etag(body)
        etag2 = compute_etag(body)
        assert etag1 == etag2


class TestCheckETagMatch:
    """Tests for check_etag_match function."""

    def test_check_etag_match_exact(self) -> None:
        """Test exact ETag matching."""
        assert check_etag_match('"abc123"', '"abc123"') is True
        assert check_etag_match('"abc123"', '"different"') is False

    def test_check_etag_match_wildcard(self) -> None:
        """Test wildcard ETag matching."""
        assert check_etag_match("*", '"any-value"') is True

    def test_check_etag_match_multiple(self) -> None:
        """Test multiple ETags in If-None-Match."""
        assert check_etag_match('"a", "b", "c"', '"b"') is True
        assert check_etag_match('"a", "b", "c"', '"d"') is False

    def test_check_etag_match_weak(self) -> None:
        """Test weak ETag comparison (W/ prefix is ignored)."""
        assert check_etag_match('W/"abc123"', '"abc123"') is True
        assert check_etag_match('"abc123"', 'W/"abc123"') is True


class TestIfModifiedSince:
    """Tests for If-Modified-Since related functions."""

    def test_parse_if_modified_since_valid(self) -> None:
        """Test parsing valid If-Modified-Since header."""
        dt = parse_if_modified_since("Sat, 15 Jan 2024 10:30:00 GMT")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_parse_if_modified_since_invalid(self) -> None:
        """Test parsing invalid If-Modified-Since header returns None."""
        assert parse_if_modified_since("invalid date") is None

    def test_format_last_modified(self) -> None:
        """Test Last-Modified header formatting."""
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        formatted = format_last_modified(dt)

        assert "15 Jan 2024" in formatted
        assert "10:30:00" in formatted
        assert "GMT" in formatted


class TestExtractLastModified:
    """Tests for extract_last_modified function."""

    def test_extract_last_modified_static(self) -> None:
        """Test extracting static Last-Modified value."""
        static = datetime(2024, 1, 15)
        response = Response(content=b"{}")

        result = extract_last_modified(response, static, None, "%Y-%m-%d")
        assert result == static

    def test_extract_last_modified_from_field(self) -> None:
        """Test extracting Last-Modified from response field."""
        response = Response(content=b'{"updated_at": "2024-01-15T10:30:00"}')

        result = extract_last_modified(
            response, None, "updated_at", "%Y-%m-%dT%H:%M:%S"
        )
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_extract_last_modified_from_nested_field(self) -> None:
        """Test extracting Last-Modified from nested response field."""
        response = Response(
            content=b'{"data": "test", "metadata": {"modified": "2024-01-15T10:30:00"}}'
        )

        result = extract_last_modified(
            response, None, "metadata.modified", "%Y-%m-%dT%H:%M:%S"
        )
        assert result is not None
        assert result.year == 2024

    def test_extract_last_modified_iso_format(self) -> None:
        """Test extracting Last-Modified with ISO format."""
        response = Response(content=b'{"updated_at": "2024-01-15T10:30:00Z"}')

        result = extract_last_modified(
            response, None, "updated_at", "%Y-%m-%dT%H:%M:%S"
        )
        assert result is not None

    def test_extract_last_modified_unix_timestamp(self) -> None:
        """Test extracting Last-Modified from unix timestamp."""
        response = Response(content=b'{"updated_at": 1705314600}')

        result = extract_last_modified(
            response, None, "updated_at", "%Y-%m-%dT%H:%M:%S"
        )
        assert result is not None

    def test_extract_last_modified_field_not_found(self) -> None:
        """Test that missing field returns None."""
        response = Response(content=b'{"other": "value"}')

        result = extract_last_modified(
            response, None, "updated_at", "%Y-%m-%dT%H:%M:%S"
        )
        assert result is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestETagIntegration:
    """Integration tests for @etag decorator."""

    @pytest.fixture
    def app(self) -> Pykour:
        """Create test application."""
        return Pykour(routes_dir="tests/routes")

    @pytest.mark.asyncio
    async def test_etag_header_added_to_response(self, app: Pykour) -> None:
        """Test that ETag header is automatically added."""

        @etag()
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test")

        assert response.status_code == 200
        assert "etag" in response.headers
        assert response.headers["etag"].startswith('"')

    @pytest.mark.asyncio
    async def test_etag_304_on_match(self, app: Pykour) -> None:
        """Test 304 response when If-None-Match matches."""

        @etag()
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)

        # First request to get ETag
        response1 = await client.get("/test")
        etag_value = response1.headers["etag"]

        # Second request with If-None-Match
        response2 = await client.get("/test", headers={"If-None-Match": etag_value})

        assert response2.status_code == 304
        assert response2.body == b""
        assert response2.headers["etag"] == etag_value

    @pytest.mark.asyncio
    async def test_etag_no_304_on_mismatch(self, app: Pykour) -> None:
        """Test normal response when If-None-Match does not match."""

        @etag()
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test", headers={"If-None-Match": '"wrong-etag"'})

        assert response.status_code == 200
        assert response.json() == {"data": "test"}

    @pytest.mark.asyncio
    async def test_etag_weak(self, app: Pykour) -> None:
        """Test weak ETag generation."""

        @etag(weak=True)
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test")

        assert response.headers["etag"].startswith('W/"')


class TestLastModifiedIntegration:
    """Integration tests for @last_modified decorator."""

    @pytest.fixture
    def app(self) -> Pykour:
        """Create test application."""
        return Pykour(routes_dir="tests/routes")

    @pytest.mark.asyncio
    async def test_last_modified_header_static(self, app: Pykour) -> None:
        """Test static Last-Modified header."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        @last_modified(value=fixed_time)
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test")

        assert response.status_code == 200
        assert "last-modified" in response.headers

    @pytest.mark.asyncio
    async def test_last_modified_header_from_field(self, app: Pykour) -> None:
        """Test Last-Modified extracted from response field."""

        @last_modified(field="updated_at")
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test", "updated_at": "2024-01-15T10:30:00Z"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test")

        assert response.status_code == 200
        assert "last-modified" in response.headers

    @pytest.mark.asyncio
    async def test_last_modified_304_on_not_modified(self, app: Pykour) -> None:
        """Test 304 when resource not modified since."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        @last_modified(value=fixed_time)
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)

        # Request with If-Modified-Since after Last-Modified
        response = await client.get(
            "/test", headers={"If-Modified-Since": "Mon, 16 Jan 2024 00:00:00 GMT"}
        )

        assert response.status_code == 304
        assert response.body == b""


class TestETagWithCache:
    """Integration tests for ETag with cache."""

    @pytest.fixture
    def storage(self) -> InMemoryStorage:
        return InMemoryStorage()

    @pytest.mark.asyncio
    async def test_etag_304_from_cache_without_handler(
        self, storage: InMemoryStorage
    ) -> None:
        """Test 304 from cached response without executing handler."""
        call_count = 0

        @cache(key="test", ttl=300)
        @etag()
        async def handler(request: Request) -> JSONResponse:
            nonlocal call_count
            call_count += 1
            return JSONResponse({"count": call_count})

        app = Pykour(routes_dir="tests/routes", cache=storage)
        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)

        # First request - populates cache
        response1 = await client.get("/test")
        assert response1.status_code == 200
        assert call_count == 1
        etag_value = response1.headers["etag"]

        # Second request with If-None-Match - should use cache and return 304
        response2 = await client.get("/test", headers={"If-None-Match": etag_value})

        assert response2.status_code == 304
        assert call_count == 1  # Handler NOT called


class TestCombinedETagAndLastModified:
    """Tests for using both @etag and @last_modified together."""

    @pytest.fixture
    def app(self) -> Pykour:
        """Create test application."""
        return Pykour(routes_dir="tests/routes")

    @pytest.mark.asyncio
    async def test_both_headers_present(self, app: Pykour) -> None:
        """Test that both ETag and Last-Modified are set."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        @etag()
        @last_modified(value=fixed_time)
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test")

        assert "etag" in response.headers
        assert "last-modified" in response.headers

    @pytest.mark.asyncio
    async def test_304_includes_both_headers(self, app: Pykour) -> None:
        """Test that 304 response includes both ETag and Last-Modified."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        @etag()
        @last_modified(value=fixed_time)
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)

        # Get ETag first
        response1 = await client.get("/test")
        etag_value = response1.headers["etag"]

        # Request with If-None-Match (ETag check happens first)
        response2 = await client.get("/test", headers={"If-None-Match": etag_value})

        assert response2.status_code == 304
        assert "etag" in response2.headers

    @pytest.mark.asyncio
    async def test_last_modified_304_includes_etag(self, app: Pykour) -> None:
        """Test that Last-Modified 304 includes ETag if present."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        @etag()
        @last_modified(value=fixed_time)
        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)

        # Request with If-Modified-Since (after checking ETag mismatch)
        response = await client.get(
            "/test",
            headers={
                "If-None-Match": '"wrong-etag"',  # ETag won't match
                "If-Modified-Since": "Mon, 16 Jan 2024 00:00:00 GMT",  # But this will
            },
        )

        assert response.status_code == 304
        assert "last-modified" in response.headers
        assert "etag" in response.headers


class TestNoDecoratorNoConditional:
    """Tests to ensure conditional processing doesn't affect non-decorated handlers."""

    @pytest.fixture
    def app(self) -> Pykour:
        """Create test application."""
        return Pykour(routes_dir="tests/routes")

    @pytest.mark.asyncio
    async def test_no_etag_header_without_decorator(self, app: Pykour) -> None:
        """Test that ETag is not added without @etag decorator."""

        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test")

        assert response.status_code == 200
        assert "etag" not in response.headers

    @pytest.mark.asyncio
    async def test_if_none_match_ignored_without_decorator(self, app: Pykour) -> None:
        """Test that If-None-Match is ignored without @etag decorator."""

        async def handler(request: Request) -> JSONResponse:
            return JSONResponse({"data": "test"})

        app._router._insert("/test", {"GET": handler})

        client = TestClient(app)
        response = await client.get("/test", headers={"If-None-Match": '"any-etag"'})

        # Should return 200, not 304
        assert response.status_code == 200
