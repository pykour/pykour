"""Tests for upload storage implementations."""

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from pykour.upload.storage.base import UploadInfo
from pykour.upload.storage.file import FileUploadStorage
from pykour.upload.storage.memory import MemoryUploadStorage


class TestUploadInfo:
    """Tests for UploadInfo dataclass."""

    def test_create_upload_info(self) -> None:
        """Test creating UploadInfo with defaults."""
        info = UploadInfo(upload_id="test-123", size=1000)

        assert info.upload_id == "test-123"
        assert info.size == 1000
        assert info.offset == 0
        assert info.filename is None
        assert info.content_type == "application/octet-stream"
        assert info.metadata == {}
        assert info.is_complete is False
        assert info.file_path is None

    def test_create_upload_info_with_metadata(self) -> None:
        """Test creating UploadInfo with full metadata."""
        info = UploadInfo(
            upload_id="test-456",
            size=2000,
            offset=500,
            filename="test.txt",
            content_type="text/plain",
            metadata={"custom": "value"},
            is_complete=True,
            file_path="/path/to/file",
        )

        assert info.upload_id == "test-456"
        assert info.size == 2000
        assert info.offset == 500
        assert info.filename == "test.txt"
        assert info.content_type == "text/plain"
        assert info.metadata == {"custom": "value"}
        assert info.is_complete is True
        assert info.file_path == "/path/to/file"


class TestMemoryUploadStorage:
    """Tests for MemoryUploadStorage."""

    @pytest.fixture
    def storage(self) -> MemoryUploadStorage:
        """Create a fresh storage instance."""
        return MemoryUploadStorage(max_size=1024 * 1024)  # 1MB

    async def test_create_upload(self, storage: MemoryUploadStorage) -> None:
        """Test creating an upload."""
        info = await storage.create(
            upload_id="test-1",
            size=100,
            metadata={"filename": "test.txt"},
        )

        assert info.upload_id == "test-1"
        assert info.size == 100
        assert info.offset == 0
        assert info.filename == "test.txt"
        assert info.is_complete is False

    async def test_get_info(self, storage: MemoryUploadStorage) -> None:
        """Test getting upload info."""
        await storage.create(upload_id="test-2", size=100)
        info = await storage.get_info("test-2")

        assert info is not None
        assert info.upload_id == "test-2"

    async def test_get_info_not_found(self, storage: MemoryUploadStorage) -> None:
        """Test getting info for non-existent upload."""
        info = await storage.get_info("non-existent")
        assert info is None

    async def test_write_chunk(self, storage: MemoryUploadStorage) -> None:
        """Test writing a chunk."""
        await storage.create(upload_id="test-3", size=100)
        new_offset = await storage.write_chunk("test-3", offset=0, data=b"Hello")

        assert new_offset == 5

        info = await storage.get_info("test-3")
        assert info is not None
        assert info.offset == 5

    async def test_write_multiple_chunks(self, storage: MemoryUploadStorage) -> None:
        """Test writing multiple chunks."""
        await storage.create(upload_id="test-4", size=10)

        offset = await storage.write_chunk("test-4", offset=0, data=b"Hello")
        assert offset == 5

        offset = await storage.write_chunk("test-4", offset=5, data=b"World")
        assert offset == 10

        data = storage.get_data("test-4")
        assert data == b"HelloWorld"

    async def test_write_chunk_offset_mismatch(
        self, storage: MemoryUploadStorage
    ) -> None:
        """Test writing chunk with wrong offset."""
        await storage.create(upload_id="test-5", size=100)

        with pytest.raises(ValueError, match="Offset mismatch"):
            await storage.write_chunk("test-5", offset=10, data=b"Hello")

    async def test_complete_upload(self, storage: MemoryUploadStorage) -> None:
        """Test completing an upload."""
        await storage.create(upload_id="test-6", size=5)
        await storage.write_chunk("test-6", offset=0, data=b"Hello")

        path = await storage.complete("test-6")

        assert path == "memory://test-6"
        info = await storage.get_info("test-6")
        assert info is not None
        assert info.is_complete is True

    async def test_complete_incomplete_upload(
        self, storage: MemoryUploadStorage
    ) -> None:
        """Test completing an incomplete upload."""
        await storage.create(upload_id="test-7", size=100)
        await storage.write_chunk("test-7", offset=0, data=b"Hello")

        with pytest.raises(ValueError, match="incomplete"):
            await storage.complete("test-7")

    async def test_delete_upload(self, storage: MemoryUploadStorage) -> None:
        """Test deleting an upload."""
        await storage.create(upload_id="test-8", size=100)
        await storage.delete("test-8")

        info = await storage.get_info("test-8")
        assert info is None

    async def test_max_size_exceeded(self, storage: MemoryUploadStorage) -> None:
        """Test exceeding max storage size."""
        # Create upload near max size
        await storage.create(upload_id="large-1", size=storage._max_size - 100)

        # Try to create another that would exceed
        with pytest.raises(ValueError, match="exceed"):
            await storage.create(upload_id="large-2", size=200)

    async def test_get_chunk(self, storage: MemoryUploadStorage) -> None:
        """Test reading a chunk."""
        await storage.create(upload_id="test-9", size=10)
        await storage.write_chunk("test-9", offset=0, data=b"HelloWorld")

        chunk = await storage.get_chunk("test-9", offset=0, length=5)
        assert chunk == b"Hello"

        chunk = await storage.get_chunk("test-9", offset=5, length=5)
        assert chunk == b"World"

    def test_clear(self, storage: MemoryUploadStorage) -> None:
        """Test clearing all uploads."""
        # Sync test - just verify clear works
        storage.clear()
        assert storage.total_size == 0


class TestFileUploadStorage:
    """Tests for FileUploadStorage."""

    @pytest.fixture
    def temp_dir(self) -> Iterator[str]:
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def storage(self, temp_dir: str) -> FileUploadStorage:
        """Create a storage instance with temp directory."""
        return FileUploadStorage(base_dir=temp_dir, expiration=3600)

    async def test_create_upload(self, storage: FileUploadStorage) -> None:
        """Test creating an upload."""
        info = await storage.create(
            upload_id="file-test-1",
            size=100,
            metadata={"filename": "test.txt"},
        )

        assert info.upload_id == "file-test-1"
        assert info.size == 100
        assert info.offset == 0
        assert info.filename == "test.txt"

        # Check files were created
        assert storage._data_path("file-test-1").exists()
        assert storage._meta_path("file-test-1").exists()

    async def test_get_info(self, storage: FileUploadStorage) -> None:
        """Test getting upload info."""
        await storage.create(upload_id="file-test-2", size=100)
        info = await storage.get_info("file-test-2")

        assert info is not None
        assert info.upload_id == "file-test-2"

    async def test_get_info_not_found(self, storage: FileUploadStorage) -> None:
        """Test getting info for non-existent upload."""
        info = await storage.get_info("non-existent")
        assert info is None

    async def test_write_chunk(self, storage: FileUploadStorage) -> None:
        """Test writing a chunk."""
        await storage.create(upload_id="file-test-3", size=100)
        new_offset = await storage.write_chunk("file-test-3", offset=0, data=b"Hello")

        assert new_offset == 5

        info = await storage.get_info("file-test-3")
        assert info is not None
        assert info.offset == 5

    async def test_write_multiple_chunks(self, storage: FileUploadStorage) -> None:
        """Test writing multiple chunks."""
        await storage.create(upload_id="file-test-4", size=10)

        offset = await storage.write_chunk("file-test-4", offset=0, data=b"Hello")
        assert offset == 5

        offset = await storage.write_chunk("file-test-4", offset=5, data=b"World")
        assert offset == 10

        # Read back data
        chunk = await storage.get_chunk("file-test-4", offset=0, length=10)
        assert chunk == b"HelloWorld"

    async def test_complete_upload(self, storage: FileUploadStorage) -> None:
        """Test completing an upload."""
        await storage.create(
            upload_id="file-test-5",
            size=5,
            metadata={"filename": "completed.txt"},
        )
        await storage.write_chunk("file-test-5", offset=0, data=b"Hello")

        path = await storage.complete("file-test-5")

        assert "completed.txt" in path
        assert Path(path).exists()

        # Read completed file content
        with open(path, "rb") as f:
            assert f.read() == b"Hello"

    async def test_complete_upload_no_filename(
        self, storage: FileUploadStorage
    ) -> None:
        """Test completing an upload without filename."""
        await storage.create(upload_id="file-test-6", size=5)
        await storage.write_chunk("file-test-6", offset=0, data=b"Hello")

        path = await storage.complete("file-test-6")

        # Should use upload_id as filename
        assert "file-test-6" in path
        assert Path(path).exists()

    async def test_delete_upload(self, storage: FileUploadStorage) -> None:
        """Test deleting an upload."""
        await storage.create(upload_id="file-test-7", size=100)
        await storage.delete("file-test-7")

        info = await storage.get_info("file-test-7")
        assert info is None
        assert not storage._data_path("file-test-7").exists()
        assert not storage._meta_path("file-test-7").exists()

    async def test_filename_conflict_resolution(
        self, storage: FileUploadStorage
    ) -> None:
        """Test handling filename conflicts."""
        # Create and complete first upload
        await storage.create(
            upload_id="conflict-1",
            size=5,
            metadata={"filename": "same.txt"},
        )
        await storage.write_chunk("conflict-1", offset=0, data=b"First")
        path1 = await storage.complete("conflict-1")

        # Create and complete second upload with same filename
        await storage.create(
            upload_id="conflict-2",
            size=6,
            metadata={"filename": "same.txt"},
        )
        await storage.write_chunk("conflict-2", offset=0, data=b"Second")
        path2 = await storage.complete("conflict-2")

        # Both should exist with different names
        assert Path(path1).exists()
        assert Path(path2).exists()
        assert path1 != path2
