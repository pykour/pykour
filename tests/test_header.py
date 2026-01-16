"""Tests for header decorator and Response header methods."""

from typing import Any

from pykour.header import (
    HEADER_REGISTRY_ATTR,
    HeaderInfo,
    get_header_info,
    header,
)
from pykour.response import JSONResponse, Response


class TestHeaderDecorator:
    """Tests for @header decorator."""

    def test_header_adds_metadata(self) -> None:
        """Test that @header adds HeaderInfo metadata to function."""

        @header("X-API-Version", "1.0")
        async def handler() -> dict[str, Any]:
            return {}

        assert hasattr(handler, HEADER_REGISTRY_ATTR)
        infos = getattr(handler, HEADER_REGISTRY_ATTR)
        assert len(infos) == 1
        assert infos[0].name == "X-API-Version"
        assert infos[0].value_template == "1.0"
        assert infos[0].condition is None

    def test_header_with_template(self) -> None:
        """Test @header with template placeholders."""

        @header("Location", "/users/{id}")
        async def handler() -> dict[str, Any]:
            return {}

        infos = get_header_info(handler)
        assert len(infos) == 1
        assert infos[0].value_template == "/users/{id}"

    def test_header_stacking(self) -> None:
        """Test multiple @header decorators on same function."""

        @header("X-Request-Id", "{request_id}")
        @header("X-Correlation-Id", "{correlation_id}")
        async def handler() -> dict[str, Any]:
            return {}

        infos = get_header_info(handler)
        assert len(infos) == 2
        # Order: innermost first
        assert infos[0].name == "X-Correlation-Id"
        assert infos[1].name == "X-Request-Id"

    def test_header_with_on_status_single(self) -> None:
        """Test @header with on_status for single status code."""

        @header("Location", "/users/{id}", on_status=201)
        async def handler() -> dict[str, Any]:
            return {}

        infos = get_header_info(handler)
        assert len(infos) == 1
        assert infos[0].condition is not None
        assert infos[0].condition(201) is True
        assert infos[0].condition(200) is False
        assert infos[0].condition(404) is False

    def test_header_with_on_status_multiple(self) -> None:
        """Test @header with on_status for multiple status codes."""

        @header("X-Success", "true", on_status=(200, 201, 204))
        async def handler() -> dict[str, Any]:
            return {}

        infos = get_header_info(handler)
        assert len(infos) == 1
        assert infos[0].condition is not None
        assert infos[0].condition(200) is True
        assert infos[0].condition(201) is True
        assert infos[0].condition(204) is True
        assert infos[0].condition(404) is False
        assert infos[0].condition(500) is False

    def test_no_decorator(self) -> None:
        """Test functions without decorator."""

        async def plain_func() -> dict[str, Any]:
            return {}

        infos = get_header_info(plain_func)
        assert infos == []

    def test_sync_function(self) -> None:
        """Test decorator works with sync functions."""

        @header("X-Sync", "true")
        def sync_handler() -> dict[str, Any]:
            return {}

        infos = get_header_info(sync_handler)
        assert len(infos) == 1
        assert infos[0].name == "X-Sync"


class TestHeaderInfo:
    """Tests for HeaderInfo dataclass."""

    def test_defaults(self) -> None:
        """Test HeaderInfo default values."""
        info = HeaderInfo(name="X-Test", value_template="value")
        assert info.name == "X-Test"
        assert info.value_template == "value"
        assert info.condition is None

    def test_with_condition(self) -> None:
        """Test HeaderInfo with condition."""

        def condition(code: int) -> bool:
            return code == 201

        info = HeaderInfo(name="Location", value_template="/test", condition=condition)
        assert info.name == "Location"
        assert info.value_template == "/test"
        assert info.condition is not None
        assert info.condition(201) is True
        assert info.condition(200) is False


class TestResponseAddHeader:
    """Tests for Response.add_header method."""

    def test_add_header_appends(self) -> None:
        """Test add_header appends to existing headers."""
        response = Response(content=b"test")
        response.add_header("X-Custom", "value1")
        response.add_header("X-Another", "value2")

        assert ("X-Custom", "value1") in response.headers
        assert ("X-Another", "value2") in response.headers

    def test_add_header_allows_duplicates(self) -> None:
        """Test add_header allows duplicate header names."""
        response = Response(content=b"test")
        response.add_header("X-Custom", "value1")
        response.add_header("X-Custom", "value2")

        custom_headers = [(k, v) for k, v in response.headers if k == "X-Custom"]
        assert len(custom_headers) == 2
        assert ("X-Custom", "value1") in custom_headers
        assert ("X-Custom", "value2") in custom_headers


class TestResponseSetHeader:
    """Tests for Response.set_header method."""

    def test_set_header_replaces(self) -> None:
        """Test set_header replaces existing header."""
        response = Response(content=b"test")
        response.add_header("X-Version", "1.0")
        response.set_header("X-Version", "2.0")

        version_headers = [(k, v) for k, v in response.headers if k == "X-Version"]
        assert len(version_headers) == 1
        assert version_headers[0][1] == "2.0"

    def test_set_header_case_insensitive(self) -> None:
        """Test set_header is case-insensitive."""
        response = Response(content=b"test")
        response.add_header("X-Version", "1.0")
        response.set_header("x-version", "2.0")

        # Should have replaced the original
        assert len([h for h in response.headers if h[0].lower() == "x-version"]) == 1
        assert response.get_header("X-Version") == "2.0"

    def test_set_header_adds_new(self) -> None:
        """Test set_header adds header if not exists."""
        response = Response(content=b"test")
        response.set_header("X-New", "value")

        assert ("X-New", "value") in response.headers


class TestResponseGetHeader:
    """Tests for Response.get_header method."""

    def test_get_header_found(self) -> None:
        """Test get_header returns value when found."""
        response = Response(content=b"test", headers={"X-Custom": "value"})
        assert response.get_header("X-Custom") == "value"

    def test_get_header_not_found(self) -> None:
        """Test get_header returns None when not found."""
        response = Response(content=b"test")
        assert response.get_header("X-Missing") is None

    def test_get_header_case_insensitive(self) -> None:
        """Test get_header is case-insensitive."""
        response = Response(content=b"test", headers={"X-Custom": "value"})
        assert response.get_header("x-custom") == "value"
        assert response.get_header("X-CUSTOM") == "value"

    def test_get_header_first_value(self) -> None:
        """Test get_header returns first value for duplicates."""
        response = Response(content=b"test")
        response.add_header("X-Multi", "first")
        response.add_header("X-Multi", "second")

        assert response.get_header("X-Multi") == "first"


class TestResponseRemoveHeader:
    """Tests for Response.remove_header method."""

    def test_remove_header_exists(self) -> None:
        """Test remove_header removes existing header."""
        response = Response(content=b"test", headers={"X-Remove": "value"})
        result = response.remove_header("X-Remove")

        assert result is True
        assert response.get_header("X-Remove") is None

    def test_remove_header_not_exists(self) -> None:
        """Test remove_header returns False when not found."""
        response = Response(content=b"test")
        result = response.remove_header("X-Missing")

        assert result is False

    def test_remove_header_case_insensitive(self) -> None:
        """Test remove_header is case-insensitive."""
        response = Response(content=b"test", headers={"X-Remove": "value"})
        result = response.remove_header("x-remove")

        assert result is True
        assert response.get_header("X-Remove") is None

    def test_remove_header_removes_all_duplicates(self) -> None:
        """Test remove_header removes all headers with same name."""
        response = Response(content=b"test")
        response.add_header("X-Multi", "first")
        response.add_header("X-Multi", "second")
        response.add_header("X-Multi", "third")

        result = response.remove_header("X-Multi")

        assert result is True
        assert response.get_header("X-Multi") is None
        multi_headers = [(k, v) for k, v in response.headers if k == "X-Multi"]
        assert len(multi_headers) == 0


class TestJSONResponseHeaders:
    """Tests for JSONResponse header methods."""

    def test_json_response_add_header(self) -> None:
        """Test JSONResponse inherits add_header method."""
        response = JSONResponse({"data": "value"})
        response.add_header("X-Custom", "test")

        assert response.get_header("X-Custom") == "test"

    def test_json_response_constructor_headers(self) -> None:
        """Test JSONResponse can be created with headers."""
        response = JSONResponse(
            {"data": "value"},
            headers={"X-Custom": "test"},
        )

        assert response.get_header("X-Custom") == "test"
