"""Tests for FileResponse class."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from pykour.response import FileResponse
from tests.helpers import MockSend, create_noop_receive, create_scope


class TestFileResponseInit:
    """Tests for FileResponse initialization."""

    def test_file_response_basic(self) -> None:
        """FileResponse should initialize with valid file path."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
            f.write(b"Hello, World!")
            temp_path = f.name

        try:
            response = FileResponse(temp_path)
            assert response.file_size == 13
            assert response.media_type == "text/plain"
        finally:
            Path(temp_path).unlink()

    def test_file_response_file_not_found(self) -> None:
        """FileResponse should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="File not found"):
            FileResponse("/nonexistent/path/file.txt")

    def test_file_response_is_directory(self) -> None:
        """FileResponse should raise IsADirectoryError for directories."""
        with pytest.raises(IsADirectoryError, match="Path is a directory"):
            FileResponse("/tmp")

    def test_file_response_mime_type_detection(self) -> None:
        """FileResponse should auto-detect MIME type from extension."""
        test_cases = [
            (".json", "application/json"),
            (".html", "text/html"),
            (".css", "text/css"),
            (".js", None),  # May vary by system, skip exact check
            (".pdf", "application/pdf"),
            (".png", "image/png"),
            (".jpg", "image/jpeg"),
        ]

        for suffix, expected_type in test_cases:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                f.write(b"test")
                temp_path = f.name

            try:
                response = FileResponse(temp_path)
                if expected_type is not None:
                    assert response.media_type == expected_type, f"Failed for {suffix}"
            finally:
                Path(temp_path).unlink()

    def test_file_response_custom_media_type(self) -> None:
        """FileResponse should use custom media_type when provided."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test")
            temp_path = f.name

        try:
            response = FileResponse(temp_path, media_type="custom/type")
            assert response.media_type == "custom/type"
        finally:
            Path(temp_path).unlink()

    def test_file_response_unknown_extension(self) -> None:
        """FileResponse should default to octet-stream for unknown types."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".unknown123") as f:
            f.write(b"test")
            temp_path = f.name

        try:
            response = FileResponse(temp_path)
            assert response.media_type == "application/octet-stream"
        finally:
            Path(temp_path).unlink()


class TestFileResponseStreaming:
    """Tests for FileResponse streaming functionality."""

    @pytest.mark.asyncio
    async def test_file_response_sends_file(self) -> None:
        """FileResponse should stream file content."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"Hello, World!")
            temp_path = f.name

        try:
            response = FileResponse(temp_path)
            send = MockSend()
            scope = create_scope()
            receive = create_noop_receive()

            await response(scope, receive, send)

            # Check headers message
            assert send.messages[0]["type"] == "http.response.start"
            assert send.messages[0]["status"] == 200

            headers = dict(send.messages[0]["headers"])
            assert b"content-length" in headers
            assert headers[b"content-length"] == b"13"
            assert b"content-type" in headers

            # Check body - collect all body chunks
            body_parts = []
            for msg in send.messages[1:]:
                if msg["type"] == "http.response.body":
                    body_parts.append(msg.get("body", b""))

            body = b"".join(body_parts)
            assert body == b"Hello, World!"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_file_response_empty_file(self) -> None:
        """FileResponse should handle empty files."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            # Write nothing - empty file
            temp_path = f.name

        try:
            response = FileResponse(temp_path)
            assert response.file_size == 0

            send = MockSend()
            scope = create_scope()
            receive = create_noop_receive()

            await response(scope, receive, send)

            # Check content-length is 0
            headers = dict(send.messages[0]["headers"])
            assert headers[b"content-length"] == b"0"

            # Body should be empty
            assert send.messages[1]["body"] == b""
            assert send.messages[1].get("more_body", False) is False
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_file_response_chunked_large_file(self) -> None:
        """FileResponse should send large files in chunks."""
        # Create file larger than chunk size
        chunk_size = 1024
        data = b"x" * (chunk_size * 3 + 100)

        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
            temp_path = f.name

        try:
            response = FileResponse(temp_path, chunk_size=chunk_size)
            send = MockSend()
            scope = create_scope()
            receive = create_noop_receive()

            await response(scope, receive, send)

            # Should have multiple body messages
            body_messages = [
                m for m in send.messages if m["type"] == "http.response.body"
            ]
            assert len(body_messages) >= 3

            # Verify chunking with more_body flag
            for msg in body_messages[:-1]:
                assert msg.get("more_body", False) is True
            assert body_messages[-1].get("more_body", False) is False

            # Verify total content matches
            body = b"".join(m.get("body", b"") for m in body_messages)
            assert body == data
        finally:
            Path(temp_path).unlink()


class TestFileResponseHeaders:
    """Tests for FileResponse header handling."""

    @pytest.mark.asyncio
    async def test_file_response_content_disposition(self) -> None:
        """FileResponse should set Content-Disposition when filename provided."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            temp_path = f.name

        try:
            response = FileResponse(temp_path, filename="report.pdf")
            send = MockSend()
            scope = create_scope()
            receive = create_noop_receive()

            await response(scope, receive, send)

            headers = dict(send.messages[0]["headers"])
            assert b"content-disposition" in headers
            assert b"report.pdf" in headers[b"content-disposition"]
            assert b"attachment" in headers[b"content-disposition"]
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_file_response_custom_headers(self) -> None:
        """FileResponse should include custom headers."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            temp_path = f.name

        try:
            response = FileResponse(
                temp_path,
                headers={"X-Custom-Header": "custom-value"},
            )
            send = MockSend()
            scope = create_scope()
            receive = create_noop_receive()

            await response(scope, receive, send)

            headers = dict(send.messages[0]["headers"])
            assert b"X-Custom-Header" in headers
            assert headers[b"X-Custom-Header"] == b"custom-value"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_file_response_custom_status_code(self) -> None:
        """FileResponse should use custom status code."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            temp_path = f.name

        try:
            response = FileResponse(temp_path, status_code=206)
            send = MockSend()
            scope = create_scope()
            receive = create_noop_receive()

            await response(scope, receive, send)

            assert send.messages[0]["status"] == 206
        finally:
            Path(temp_path).unlink()


class TestFileResponseExport:
    """Tests for FileResponse export."""

    def test_file_response_exported(self) -> None:
        """FileResponse should be exported from pykour package."""
        from pykour import FileResponse as ExportedFileResponse

        assert ExportedFileResponse is FileResponse
