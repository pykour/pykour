"""In-memory upload storage for testing.

This module provides an in-memory storage backend that is useful for
testing and development. Data is not persisted between restarts.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, BinaryIO

from pykour.upload.storage.base import UploadInfo, UploadStorage


class MemoryUploadStorage(UploadStorage):
    """In-memory storage backend for file uploads.

    This storage backend keeps all data in memory. It is primarily
    intended for testing and development purposes.

    Warning:
        Data is lost when the process restarts. Do not use in production.

    Example:
        storage = MemoryUploadStorage(max_size=100 * 1024 * 1024)  # 100MB

        # Use in tests
        info = await storage.create(upload_id, size=1000)
        await storage.write_chunk(upload_id, offset=0, data=b"test")

        # Clear all data
        storage.clear()
    """

    def __init__(
        self,
        max_size: int = 1024 * 1024 * 1024,  # 1GB
        expiration: int = 86400,  # 24 hours
    ) -> None:
        """Initialize in-memory storage.

        Args:
            max_size: Maximum total size of all uploads in bytes.
            expiration: Seconds until incomplete uploads expire.
        """
        self._max_size = max_size
        self._expiration = expiration
        self._uploads: dict[str, UploadInfo] = {}
        self._data: dict[str, bytearray] = {}

    @property
    def total_size(self) -> int:
        """Get total size of all uploads."""
        return sum(info.size for info in self._uploads.values())

    def clear(self) -> None:
        """Clear all uploads from memory."""
        self._uploads.clear()
        self._data.clear()

    async def create(
        self,
        upload_id: str,
        size: int,
        metadata: dict[str, Any] | None = None,
    ) -> UploadInfo:
        """Create a new upload.

        Args:
            upload_id: Unique identifier for the upload.
            size: Total size of the upload in bytes.
            metadata: Optional metadata (filename, content_type, etc.).

        Returns:
            UploadInfo for the created upload.

        Raises:
            ValueError: If max_size would be exceeded.
        """
        if self.total_size + size > self._max_size:
            raise ValueError(
                f"Upload would exceed max storage size: "
                f"{self.total_size + size} > {self._max_size}"
            )

        metadata = metadata or {}
        now = datetime.now()
        expires_at = now + timedelta(seconds=self._expiration)

        info = UploadInfo(
            upload_id=upload_id,
            size=size,
            offset=0,
            filename=metadata.get("filename"),
            content_type=metadata.get("content_type", "application/octet-stream"),
            metadata=metadata,
            created_at=now,
            expires_at=expires_at,
            is_complete=False,
        )

        self._uploads[upload_id] = info
        self._data[upload_id] = bytearray(size)

        return info

    async def get_info(self, upload_id: str) -> UploadInfo | None:
        """Get information about an upload.

        Args:
            upload_id: The upload identifier.

        Returns:
            UploadInfo if found, None otherwise.
        """
        info = self._uploads.get(upload_id)
        if info is None:
            return None

        # Check if expired
        if (
            info.expires_at
            and datetime.now() > info.expires_at
            and not info.is_complete
        ):
            await self.delete(upload_id)
            return None

        return info

    async def write_chunk(
        self,
        upload_id: str,
        offset: int,
        data: bytes | BinaryIO,
    ) -> int:
        """Write a chunk of data to the upload.

        Args:
            upload_id: The upload identifier.
            offset: Byte offset where the chunk should be written.
            data: The data to write (bytes or file-like object).

        Returns:
            New offset after writing (offset + bytes written).

        Raises:
            ValueError: If upload not found or offset mismatch.
        """
        info = await self.get_info(upload_id)
        if info is None:
            raise ValueError(f"Upload {upload_id} not found")

        if offset != info.offset:
            raise ValueError(f"Offset mismatch: expected {info.offset}, got {offset}")

        # Read data if it's a file-like object
        if hasattr(data, "read"):
            data = data.read()  # type: ignore[union-attr]

        chunk_size = len(data)

        # Check bounds
        if offset + chunk_size > info.size:
            raise ValueError(
                f"Chunk would exceed upload size: {offset + chunk_size} > {info.size}"
            )

        # Write data
        buffer = self._data.get(upload_id)
        if buffer is None:
            raise ValueError(f"Upload {upload_id} data not found")

        buffer[offset : offset + chunk_size] = data

        # Update offset
        info.offset = offset + chunk_size

        return info.offset

    async def complete(self, upload_id: str) -> str:
        """Mark an upload as complete.

        Args:
            upload_id: The upload identifier.

        Returns:
            Virtual path to the completed file.

        Raises:
            ValueError: If upload not found or incomplete.
        """
        info = await self.get_info(upload_id)
        if info is None:
            raise ValueError(f"Upload {upload_id} not found")

        if info.offset < info.size:
            raise ValueError(
                f"Upload incomplete: received {info.offset} of {info.size} bytes"
            )

        info.is_complete = True
        info.expires_at = None
        info.file_path = f"memory://{upload_id}"

        return info.file_path

    async def delete(self, upload_id: str) -> None:
        """Delete an upload and its data.

        Args:
            upload_id: The upload identifier.
        """
        self._uploads.pop(upload_id, None)
        self._data.pop(upload_id, None)

    async def cleanup_expired(self) -> int:
        """Clean up expired uploads.

        Returns:
            Number of uploads cleaned up.
        """
        count = 0
        now = datetime.now()
        expired_ids = []

        for upload_id, info in self._uploads.items():
            if info.expires_at and now > info.expires_at and not info.is_complete:
                expired_ids.append(upload_id)

        for upload_id in expired_ids:
            await self.delete(upload_id)
            count += 1

        return count

    async def get_chunk(
        self,
        upload_id: str,
        offset: int,
        length: int,
    ) -> bytes:
        """Read a chunk of data from an upload.

        Args:
            upload_id: The upload identifier.
            offset: Byte offset to start reading from.
            length: Number of bytes to read.

        Returns:
            The requested chunk of data.
        """
        info = await self.get_info(upload_id)
        if info is None:
            raise ValueError(f"Upload {upload_id} not found")

        buffer = self._data.get(upload_id)
        if buffer is None:
            raise ValueError(f"Upload {upload_id} data not found")

        return bytes(buffer[offset : offset + length])

    def get_data(self, upload_id: str) -> bytes | None:
        """Get complete data for an upload (testing helper).

        Args:
            upload_id: The upload identifier.

        Returns:
            Complete upload data or None if not found.
        """
        buffer = self._data.get(upload_id)
        if buffer is None:
            return None
        return bytes(buffer)
