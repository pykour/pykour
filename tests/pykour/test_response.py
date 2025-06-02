import json
import pytest
from unittest.mock import AsyncMock

from pykour.response import Response
from pykour.headers import Headers


@pytest.mark.asyncio
class TestResponse:
    async def test_init_default(self):
        """Test Response initialization with default values"""
        response = Response()
        assert response.status == 200
        assert response._body is None
        assert isinstance(response._headers, Headers)
        assert len(response._headers) == 0

    async def test_init_with_bytes_body(self):
        """Test Response initialization with bytes body"""
        body = b"Hello, World!"
        response = Response(body=body, status=201)
        assert response.status == 201
        assert response._body == body

    async def test_init_with_str_body(self):
        """Test Response initialization with string body"""
        body = "Hello, World!"
        response = Response(body=body, status=200)
        assert response._body == body

    async def test_init_with_dict_body(self):
        """Test Response initialization with dict body"""
        body = {"message": "Hello", "count": 42}
        response = Response(body=body, status=200)
        assert response._body == body

    async def test_init_with_dict_headers(self):
        """Test Response initialization with dict headers"""
        headers = {"Content-Type": "application/json", "X-Custom": "value"}
        response = Response(headers=headers)
        assert "content-type" in response._headers
        assert "x-custom" in response._headers
        assert response._headers["content-type"] == "application/json"
        assert response._headers["x-custom"] == "value"

    async def test_init_with_headers_object(self):
        """Test Response initialization with Headers object"""
        headers = Headers([])
        headers["Content-Type"] = "application/json"
        headers["X-Custom"] = "value"
        
        response = Response(headers=headers)
        assert "content-type" in response._headers
        assert "x-custom" in response._headers
        assert response._headers["content-type"] == "application/json"
        assert response._headers["x-custom"] == "value"
        # Ensure it's a copy
        assert response._headers is not headers

    async def test_prepare_headers_with_dict(self):
        """Test _prepare_headers with dict input"""
        response = Response()
        headers = {"Content-Type": "text/html", "X-Test": "value"}
        result = response._prepare_headers(headers)
        
        assert isinstance(result, Headers)
        assert "content-type" in result
        assert "x-test" in result
        assert result["content-type"] == "text/html"
        assert result["x-test"] == "value"

    async def test_prepare_headers_with_headers_object(self):
        """Test _prepare_headers with Headers object input"""
        response = Response()
        headers = Headers([])
        headers["Content-Type"] = "text/html"
        headers["X-Test"] = "value"
        
        result = response._prepare_headers(headers)
        assert isinstance(result, Headers)
        assert result is not headers  # Should be a copy
        assert result == headers  # But equal in content

    async def test_prepare_body_none(self):
        """Test _prepare_body with None body"""
        response = Response(body=None)
        result = response._prepare_body()
        assert result == b""

    async def test_prepare_body_bytes(self):
        """Test _prepare_body with bytes body"""
        body = b"Hello, bytes!"
        response = Response(body=body)
        result = response._prepare_body()
        assert result == body

    async def test_prepare_body_str_without_content_type(self):
        """Test _prepare_body with string body without content-type header"""
        body = "Hello, string!"
        response = Response(body=body)
        result = response._prepare_body()
        
        assert result == body.encode("utf-8")
        assert "content-type" in response._headers
        assert response._headers["content-type"] == "text/plain; charset=utf-8"

    async def test_prepare_body_str_with_content_type(self):
        """Test _prepare_body with string body with existing content-type header"""
        body = "Hello, string!"
        headers = {"Content-Type": "text/html; charset=utf-8"}
        response = Response(body=body, headers=headers)
        result = response._prepare_body()
        
        assert result == body.encode("utf-8")
        assert response._headers["content-type"] == "text/html; charset=utf-8"

    async def test_prepare_body_dict_without_content_type(self):
        """Test _prepare_body with dict body without content-type header"""
        body = {"message": "Hello", "count": 42}
        response = Response(body=body)
        result = response._prepare_body()
        
        expected = json.dumps(body).encode("utf-8")
        assert result == expected
        assert "content-type" in response._headers
        assert response._headers["content-type"] == "application/json"

    async def test_prepare_body_dict_with_content_type(self):
        """Test _prepare_body with dict body with existing content-type header"""
        body = {"message": "Hello", "count": 42}
        headers = {"Content-Type": "application/json; charset=utf-8"}
        response = Response(body=body, headers=headers)
        result = response._prepare_body()
        
        expected = json.dumps(body).encode("utf-8")
        assert result == expected
        assert response._headers["content-type"] == "application/json; charset=utf-8"

    async def test_prepare_body_unsupported_type(self):
        """Test _prepare_body with unsupported body type"""
        response = Response(body=12345)  # Integer is not supported
        
        with pytest.raises(TypeError, match="Unsupported body type"):
            response._prepare_body()

    async def test_send_with_empty_body(self):
        """Test send method with empty body"""
        send_mock = AsyncMock()
        response = Response(body=None, status=204)
        
        await response.send(send_mock)
        
        # Check calls
        assert send_mock.call_count == 2
        
        # First call - response start
        first_call = send_mock.call_args_list[0]
        assert first_call[0][0]["type"] == "http.response.start"
        assert first_call[0][0]["status"] == 204
        assert first_call[0][0]["headers"] == []
        
        # Second call - response body
        second_call = send_mock.call_args_list[1]
        assert second_call[0][0]["type"] == "http.response.body"
        assert second_call[0][0]["body"] == b""

    async def test_send_with_string_body(self):
        """Test send method with string body"""
        send_mock = AsyncMock()
        body = "Hello, World!"
        response = Response(body=body, status=200)
        
        await response.send(send_mock)
        
        # Check calls
        assert send_mock.call_count == 2
        
        # First call - response start
        first_call = send_mock.call_args_list[0]
        assert first_call[0][0]["type"] == "http.response.start"
        assert first_call[0][0]["status"] == 200
        
        headers_dict = {h[0]: h[1] for h in first_call[0][0]["headers"]}
        assert headers_dict[b"content-type"] == b"text/plain; charset=utf-8"
        assert headers_dict[b"content-length"] == str(len(body.encode("utf-8"))).encode("latin1")
        
        # Second call - response body
        second_call = send_mock.call_args_list[1]
        assert second_call[0][0]["type"] == "http.response.body"
        assert second_call[0][0]["body"] == body.encode("utf-8")

    async def test_send_with_dict_body(self):
        """Test send method with dict body"""
        send_mock = AsyncMock()
        body = {"message": "Hello", "count": 42}
        response = Response(body=body, status=200)
        
        await response.send(send_mock)
        
        # Check calls
        assert send_mock.call_count == 2
        
        # First call - response start
        first_call = send_mock.call_args_list[0]
        assert first_call[0][0]["type"] == "http.response.start"
        assert first_call[0][0]["status"] == 200
        
        headers_dict = {h[0]: h[1] for h in first_call[0][0]["headers"]}
        assert headers_dict[b"content-type"] == b"application/json"
        body_bytes = json.dumps(body).encode("utf-8")
        assert headers_dict[b"content-length"] == str(len(body_bytes)).encode("latin1")
        
        # Second call - response body
        second_call = send_mock.call_args_list[1]
        assert second_call[0][0]["type"] == "http.response.body"
        assert second_call[0][0]["body"] == body_bytes

    async def test_send_with_custom_headers(self):
        """Test send method with custom headers"""
        send_mock = AsyncMock()
        body = "Test"
        headers = {
            "X-Custom-Header": "value",
            "Cache-Control": "no-cache"
        }
        response = Response(body=body, status=200, headers=headers)
        
        await response.send(send_mock)
        
        # First call - response start
        first_call = send_mock.call_args_list[0]
        headers_list = first_call[0][0]["headers"]
        headers_dict = {h[0].decode("latin1"): h[1].decode("latin1") for h in headers_list}
        
        assert "x-custom-header" in headers_dict
        assert headers_dict["x-custom-header"] == "value"
        assert "cache-control" in headers_dict
        assert headers_dict["cache-control"] == "no-cache"
        assert "content-type" in headers_dict
        assert "content-length" in headers_dict

    async def test_send_preserves_content_length_if_set(self):
        """Test that send method preserves content-length if already set"""
        send_mock = AsyncMock()
        body = "Test"
        headers = {"Content-Length": "100"}  # Deliberately wrong
        response = Response(body=body, headers=headers)
        
        await response.send(send_mock)
        
        # First call - response start
        first_call = send_mock.call_args_list[0]
        headers_list = first_call[0][0]["headers"]
        headers_dict = {h[0].decode("latin1"): h[1].decode("latin1") for h in headers_list}
        
        # Should preserve the manually set content-length
        assert headers_dict["content-length"] == "100"

    async def test_send_multiple_times(self):
        """Test that send can be called multiple times (idempotent behavior)"""
        send_mock = AsyncMock()
        response = Response(body="Test", status=200)
        
        # First send
        await response.send(send_mock)
        first_call_count = send_mock.call_count
        
        # Reset mock
        send_mock.reset_mock()
        
        # Second send
        await response.send(send_mock)
        second_call_count = send_mock.call_count
        
        # Should have same behavior
        assert first_call_count == second_call_count

    async def test_unicode_body(self):
        """Test Response with unicode characters in body"""
        body = "Hello, 世界! 🌍"
        response = Response(body=body)
        
        prepared_body = response._prepare_body()
        assert prepared_body == body.encode("utf-8")
        assert "content-type" in response._headers
        assert response._headers["content-type"] == "text/plain; charset=utf-8"

    async def test_complex_json_body(self):
        """Test Response with complex nested JSON body"""
        body = {
            "users": [
                {"id": 1, "name": "Alice", "tags": ["admin", "user"]},
                {"id": 2, "name": "Bob", "tags": ["user"]}
            ],
            "meta": {
                "total": 2,
                "page": 1
            }
        }
        response = Response(body=body)
        
        prepared_body = response._prepare_body()
        assert json.loads(prepared_body.decode("utf-8")) == body
        assert "content-type" in response._headers
        assert response._headers["content-type"] == "application/json"