"""Base storage abstraction for file uploads.

This module defines the abstract interface for upload storage backends,
allowing different storage mechanisms (filesystem, S3, etc.) to be
implemented with a consistent API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, BinaryIO


@dataclass
class UploadInfo:
    """Information about an upload.

    Attributes:
        upload_id: Unique identifier for the upload.
        size: Total size of the upload in bytes.
        offset: Current offset (bytes uploaded so far).
        filename: Original filename from the client.
        content_type: MIME type of the file.
        metadata: Additional metadata from the upload.
        created_at: When the upload was created.
        expires_at: When the upload expires (for cleanup).
        is_complete: Whether the upload is complete.
        file_path: Path to the stored file (after completion).
    """

    upload_id: str
    size: int
    offset: int = 0
    filename: str | None = None
    content_type: str = "application/octet-stream"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime | None = None
    is_complete: bool = False
    file_path: str | None = None


class UploadStorage(ABC):
    """Abstract base class for upload storage backends.

    This class defines the interface that all storage backends must implement.
    Storage backends handle the actual persistence of uploaded file data.

    Example:
        class S3Storage(UploadStorage):
            def __init__(self, bucket: str):
                self.bucket = bucket

            async def create(self, upload_id, size, metadata) -> UploadInfo:
                # Create upload in S3
                ...

            async def write_chunk(self, upload_id, offset, data) -> int:
                # Upload chunk to S3
                ...
    """

    @abstractmethod
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
            StorageError: If creation fails.
        """
        ...

    @abstractmethod
    async def get_info(self, upload_id: str) -> UploadInfo | None:
        """Get information about an upload.

        Args:
            upload_id: The upload identifier.

        Returns:
            UploadInfo if found, None otherwise.
        """
        ...

    @abstractmethod
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
            StorageError: If write fails.
            OffsetMismatchError: If offset doesn't match current position.
        """
        ...

    @abstractmethod
    async def complete(self, upload_id: str) -> str:
        """Mark an upload as complete and finalize storage.

        Args:
            upload_id: The upload identifier.

        Returns:
            Path or URI to the completed file.

        Raises:
            StorageError: If completion fails.
            IncompleteUploadError: If upload is not fully received.
        """
        ...

    @abstractmethod
    async def delete(self, upload_id: str) -> None:
        """Delete an upload and its data.

        Args:
            upload_id: The upload identifier.

        Raises:
            StorageError: If deletion fails.
        """
        ...

    async def cleanup_expired(self) -> int:
        """Clean up expired uploads.

        Returns:
            Number of uploads cleaned up.

        Note:
            This is optional and may not be implemented by all backends.
        """
        return 0

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

        Raises:
            StorageError: If read fails.

        Note:
            This is optional and may not be implemented by all backends.
        """
        raise NotImplementedError("get_chunk not supported by this storage backend")
