"""Tests for tus protocol implementation."""

import pytest

from pykour.upload.protocols.tus.headers import (
    TUS_VERSION,
    TusHeaders,
    build_server_headers,
    encode_metadata,
    parse_metadata,
)
from pykour.upload.protocols.tus.exceptions import (
    TusError,
    TusInvalidHeader,
    TusInvalidOffset,
    TusNotFound,
    TusSizeLimitExceeded,
    TusUnsupportedVersion,
)
from pykour.upload.protocols.tus.protocol import TusProtocol
from pykour.upload.storage.memory import MemoryUploadStorage


class TestTusHeaders:
    """Tests for tus header parsing."""

    def test_parse_basic_headers(self) -> None:
        """Test parsing basic tus headers."""
        headers = {
            "Tus-Resumable": "1.0.0",
            "Upload-Length": "1000",
            "Upload-Offset": "500",
        }
        tus_headers = TusHeaders.from_headers(headers)

        assert tus_headers.tus_resumable == "1.0.0"
        assert tus_headers.upload_length == 1000
        assert tus_headers.upload_offset == 500

    def test_parse_case_insensitive(self) -> None:
        """Test headers are parsed case-insensitively."""
        headers = {
            "tus-resumable": "1.0.0",
            "UPLOAD-LENGTH": "1000",
        }
        tus_headers = TusHeaders.from_headers(headers)

        assert tus_headers.tus_resumable == "1.0.0"
        assert tus_headers.upload_length == 1000

    def test_parse_metadata(self) -> None:
        """Test parsing Upload-Metadata header."""
        headers = {
            "Tus-Resumable": "1.0.0",
            "Upload-Metadata": "filename dGVzdC50eHQ=,mimetype dGV4dC9wbGFpbg==",
        }
        tus_headers = TusHeaders.from_headers(headers)

        assert tus_headers.upload_metadata is not None
        assert tus_headers.upload_metadata["filename"] == "test.txt"
        assert tus_headers.upload_metadata["mimetype"] == "text/plain"

    def test_parse_defer_length(self) -> None:
        """Test parsing Upload-Defer-Length header."""
        headers = {
            "Tus-Resumable": "1.0.0",
            "Upload-Defer-Length": "1",
        }
        tus_headers = TusHeaders.from_headers(headers)

        assert tus_headers.upload_defer_length is True

    def test_validate_supported_version(self) -> None:
        """Test version validation for supported version."""
        headers = TusHeaders(tus_resumable="1.0.0")
        assert headers.validate_version() is True

    def test_validate_unsupported_version(self) -> None:
        """Test version validation for unsupported version."""
        headers = TusHeaders(tus_resumable="0.2.2")
        assert headers.validate_version() is False

    def test_validate_missing_version(self) -> None:
        """Test version validation when version is missing."""
        headers = TusHeaders(tus_resumable=None)
        assert headers.validate_version() is False


class TestMetadataEncoding:
    """Tests for metadata encoding/decoding."""

    def test_parse_simple_metadata(self) -> None:
        """Test parsing simple metadata."""
        result = parse_metadata("filename dGVzdC50eHQ=")
        assert result == {"filename": "test.txt"}

    def test_parse_multiple_values(self) -> None:
        """Test parsing multiple metadata values."""
        result = parse_metadata(
            "filename dGVzdC50eHQ=,mimetype dGV4dC9wbGFpbg==,custom Y3VzdG9tX3ZhbHVl"
        )
        assert result == {
            "filename": "test.txt",
            "mimetype": "text/plain",
            "custom": "custom_value",
        }

    def test_parse_key_only(self) -> None:
        """Test parsing key without value."""
        result = parse_metadata("flag")
        assert result == {"flag": ""}

    def test_parse_empty_string(self) -> None:
        """Test parsing empty string."""
        result = parse_metadata("")
        assert result == {}

    def test_encode_metadata(self) -> None:
        """Test encoding metadata."""
        metadata = {"filename": "test.txt", "mimetype": "text/plain"}
        result = encode_metadata(metadata)

        # Parse it back to verify
        parsed = parse_metadata(result)
        assert parsed == metadata

    def test_encode_empty_value(self) -> None:
        """Test encoding key with empty value."""
        result = encode_metadata({"flag": ""})
        assert result == "flag"


class TestBuildServerHeaders:
    """Tests for building server response headers."""

    def test_build_basic_headers(self) -> None:
        """Test building basic response headers."""
        headers = build_server_headers()
        assert headers["Tus-Resumable"] == TUS_VERSION

    def test_build_with_offset(self) -> None:
        """Test building headers with offset."""
        headers = build_server_headers(upload_offset=500)
        assert headers["Upload-Offset"] == "500"

    def test_build_with_length(self) -> None:
        """Test building headers with length."""
        headers = build_server_headers(upload_length=1000)
        assert headers["Upload-Length"] == "1000"

    def test_build_with_location(self) -> None:
        """Test building headers with location."""
        headers = build_server_headers(location="/files/abc123")
        assert headers["Location"] == "/files/abc123"

    def test_build_options_headers(self) -> None:
        """Test building OPTIONS response headers."""
        headers = build_server_headers(max_size=1024 * 1024, include_options=True)

        assert "Tus-Version" in headers
        assert "Tus-Extension" in headers
        assert "Tus-Max-Size" in headers


class TestTusExceptions:
    """Tests for tus exception classes."""

    def test_base_error(self) -> None:
        """Test base TusError."""
        error = TusError("Custom message")
        assert error.message == "Custom message"
        assert error.status_code == 500

    def test_unsupported_version(self) -> None:
        """Test TusUnsupportedVersion error."""
        error = TusUnsupportedVersion()
        assert error.status_code == 412

    def test_invalid_header(self) -> None:
        """Test TusInvalidHeader error."""
        error = TusInvalidHeader("Missing Upload-Length")
        assert error.message == "Missing Upload-Length"
        assert error.status_code == 400

    def test_invalid_offset(self) -> None:
        """Test TusInvalidOffset error."""
        error = TusInvalidOffset()
        assert error.status_code == 409

    def test_not_found(self) -> None:
        """Test TusNotFound error."""
        error = TusNotFound()
        assert error.status_code == 404

    def test_size_limit_exceeded(self) -> None:
        """Test TusSizeLimitExceeded error."""
        error = TusSizeLimitExceeded()
        assert error.status_code == 413


class TestTusProtocol:
    """Tests for TusProtocol class."""

    @pytest.fixture
    def storage(self) -> MemoryUploadStorage:
        """Create a memory storage."""
        return MemoryUploadStorage()

    @pytest.fixture
    def protocol(self, storage: MemoryUploadStorage) -> TusProtocol:
        """Create a TusProtocol instance."""
        return TusProtocol(
            storage=storage,
            max_size=1024 * 1024,  # 1MB
            path_prefix="/files",
        )

    def test_protocol_name(self, protocol: TusProtocol) -> None:
        """Test protocol name."""
        assert protocol.name == "tus"

    def test_get_options_headers(self, protocol: TusProtocol) -> None:
        """Test getting OPTIONS headers."""
        headers = protocol.get_options_headers()

        assert headers["Tus-Resumable"] == TUS_VERSION
        assert "Tus-Version" in headers
        assert "Tus-Extension" in headers
        assert "Tus-Max-Size" in headers

    def test_build_location_url(self, protocol: TusProtocol) -> None:
        """Test building location URL."""
        url = protocol.build_location_url("abc123")
        assert url == "/files/abc123"

        url = protocol.build_location_url("abc123", "https://example.com")
        assert url == "https://example.com/files/abc123"

    def test_extract_upload_id(self, protocol: TusProtocol) -> None:
        """Test extracting upload ID from path."""
        upload_id = protocol._extract_upload_id("/files/abc123")
        assert upload_id == "abc123"

        upload_id = protocol._extract_upload_id("/files/abc123/extra")
        assert upload_id == "abc123"

    def test_extract_upload_id_missing(self, protocol: TusProtocol) -> None:
        """Test extracting upload ID when missing."""
        with pytest.raises(TusInvalidHeader, match="Upload ID required"):
            protocol._extract_upload_id("/files/")


class TestTusProtocolOperations:
    """Tests for TusProtocol operations using mock requests."""

    @pytest.fixture
    def storage(self) -> MemoryUploadStorage:
        """Create a memory storage."""
        return MemoryUploadStorage()

    @pytest.fixture
    def protocol(self, storage: MemoryUploadStorage) -> TusProtocol:
        """Create a TusProtocol instance."""
        return TusProtocol(
            storage=storage,
            max_size=1024 * 1024,
            path_prefix="/files",
        )

    async def test_get_upload_status_not_found(self, protocol: TusProtocol) -> None:
        """Test getting status for non-existent upload."""
        with pytest.raises(TusNotFound):
            await protocol.get_upload_status("non-existent")

    async def test_delete_upload_not_found(self, protocol: TusProtocol) -> None:
        """Test deleting non-existent upload."""
        with pytest.raises(TusNotFound):
            await protocol.delete_upload("non-existent")

    async def test_full_upload_flow(
        self, protocol: TusProtocol, storage: MemoryUploadStorage
    ) -> None:
        """Test complete upload flow using storage directly."""
        # Create upload
        info = await storage.create(
            upload_id="flow-test",
            size=10,
            metadata={"filename": "test.txt"},
        )
        assert info.offset == 0

        # Write first chunk
        new_offset = await storage.write_chunk("flow-test", offset=0, data=b"Hello")
        assert new_offset == 5

        # Get status
        result = await protocol.get_upload_status("flow-test")
        assert result.offset == 5
        assert result.size == 10
        assert result.is_complete is False

        # Write second chunk
        new_offset = await storage.write_chunk("flow-test", offset=5, data=b"World")
        assert new_offset == 10

        # Complete
        path = await storage.complete("flow-test")
        assert path == "memory://flow-test"

        # Get status after complete
        result = await protocol.get_upload_status("flow-test")
        assert result.is_complete is True

    async def test_delete_upload(
        self, protocol: TusProtocol, storage: MemoryUploadStorage
    ) -> None:
        """Test deleting an upload."""
        await storage.create(upload_id="delete-test", size=100)

        result = await protocol.delete_upload("delete-test")
        assert result.upload_id == "delete-test"

        # Should be deleted
        with pytest.raises(TusNotFound):
            await protocol.get_upload_status("delete-test")
