"""Filesystem-based upload storage.

This module provides a storage backend that persists uploads to the local filesystem.
It is suitable for single-server deployments and development.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, BinaryIO

import orjson

from pykour.upload.storage.base import UploadInfo, UploadStorage


class FileUploadStorage(UploadStorage):
    """Filesystem-based storage backend for file uploads.

    This storage backend saves uploaded files to the local filesystem.
    It maintains upload metadata in JSON files alongside the upload data.

    Directory structure:
        base_dir/
            uploads/
                {upload_id}.data      # Partial/complete upload data
                {upload_id}.meta      # Upload metadata (JSON)
            completed/
                {original_filename}   # Completed files (with deduplication)

    Example:
        storage = FileUploadStorage(
            base_dir="./uploads",
            expiration=3600,  # 1 hour
        )

        # Create upload
        info = await storage.create(upload_id, size=1000, metadata={"filename": "test.txt"})

        # Write chunks
        await storage.write_chunk(upload_id, offset=0, data=chunk1)
        await storage.write_chunk(upload_id, offset=500, data=chunk2)

        # Complete upload
        file_path = await storage.complete(upload_id)
    """

    def __init__(
        self,
        base_dir: str | Path = "./uploads",
        expiration: int = 86400,  # 24 hours
        completed_subdir: str = "completed",
        uploads_subdir: str = "uploads",
    ) -> None:
        """Initialize filesystem storage.

        Args:
            base_dir: Base directory for all upload data.
            expiration: Seconds until incomplete uploads expire.
            completed_subdir: Subdirectory for completed files.
            uploads_subdir: Subdirectory for in-progress uploads.
        """
        self._base_dir = Path(base_dir)
        self._expiration = expiration
        self._uploads_dir = self._base_dir / uploads_subdir
        self._completed_dir = self._base_dir / completed_subdir

        # Ensure directories exist
        self._uploads_dir.mkdir(parents=True, exist_ok=True)
        self._completed_dir.mkdir(parents=True, exist_ok=True)

    def _data_path(self, upload_id: str) -> Path:
        """Get path to upload data file."""
        return self._uploads_dir / f"{upload_id}.data"

    def _meta_path(self, upload_id: str) -> Path:
        """Get path to upload metadata file."""
        return self._uploads_dir / f"{upload_id}.meta"

    def _load_metadata(self, upload_id: str) -> dict[str, Any] | None:
        """Load metadata from JSON file."""
        meta_path = self._meta_path(upload_id)
        if not meta_path.exists():
            return None
        try:
            with open(meta_path, "rb") as f:
                return orjson.loads(f.read())
        except (OSError, orjson.JSONDecodeError):
            return None

    def _save_metadata(self, upload_id: str, metadata: dict[str, Any]) -> None:
        """Save metadata to JSON file."""
        meta_path = self._meta_path(upload_id)
        with open(meta_path, "wb") as f:
            f.write(orjson.dumps(metadata))

    def _metadata_to_info(self, metadata: dict[str, Any]) -> UploadInfo:
        """Convert metadata dict to UploadInfo."""
        return UploadInfo(
            upload_id=metadata["upload_id"],
            size=metadata["size"],
            offset=metadata.get("offset", 0),
            filename=metadata.get("filename"),
            content_type=metadata.get("content_type", "application/octet-stream"),
            metadata=metadata.get("metadata", {}),
            created_at=datetime.fromisoformat(metadata["created_at"]),
            expires_at=(
                datetime.fromisoformat(metadata["expires_at"])
                if metadata.get("expires_at")
                else None
            ),
            is_complete=metadata.get("is_complete", False),
            file_path=metadata.get("file_path"),
        )

    def _info_to_metadata(self, info: UploadInfo) -> dict[str, Any]:
        """Convert UploadInfo to metadata dict."""
        return {
            "upload_id": info.upload_id,
            "size": info.size,
            "offset": info.offset,
            "filename": info.filename,
            "content_type": info.content_type,
            "metadata": info.metadata,
            "created_at": info.created_at.isoformat(),
            "expires_at": info.expires_at.isoformat() if info.expires_at else None,
            "is_complete": info.is_complete,
            "file_path": info.file_path,
        }

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
        """
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

        # Create empty data file
        data_path = self._data_path(upload_id)
        await asyncio.to_thread(self._create_empty_file, data_path)

        # Save metadata
        await asyncio.to_thread(
            self._save_metadata, upload_id, self._info_to_metadata(info)
        )

        return info

    def _create_empty_file(self, path: Path) -> None:
        """Create an empty file."""
        path.touch()

    async def get_info(self, upload_id: str) -> UploadInfo | None:
        """Get information about an upload.

        Args:
            upload_id: The upload identifier.

        Returns:
            UploadInfo if found, None otherwise.
        """
        metadata = await asyncio.to_thread(self._load_metadata, upload_id)
        if metadata is None:
            return None

        info = self._metadata_to_info(metadata)

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

        # Write data to file
        data_path = self._data_path(upload_id)
        await asyncio.to_thread(self._write_to_file, data_path, offset, data)

        # Update metadata
        new_offset = offset + chunk_size
        metadata = await asyncio.to_thread(self._load_metadata, upload_id)
        if metadata:
            metadata["offset"] = new_offset
            await asyncio.to_thread(self._save_metadata, upload_id, metadata)

        return new_offset

    def _write_to_file(self, path: Path, offset: int, data: bytes) -> None:
        """Write data to file at offset."""
        with open(path, "r+b") as f:
            f.seek(offset)
            f.write(data)

    async def complete(self, upload_id: str) -> str:
        """Mark an upload as complete and finalize storage.

        Args:
            upload_id: The upload identifier.

        Returns:
            Path to the completed file.

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

        # Determine final filename
        filename = info.filename or f"{upload_id}"
        final_path = self._completed_dir / filename

        # Handle filename conflicts
        if final_path.exists():
            base, ext = os.path.splitext(filename)
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{base}_{unique_id}{ext}"
            final_path = self._completed_dir / filename

        # Move data file to completed directory
        data_path = self._data_path(upload_id)
        await asyncio.to_thread(self._move_file, data_path, final_path)

        # Update metadata
        metadata = await asyncio.to_thread(self._load_metadata, upload_id)
        if metadata:
            metadata["is_complete"] = True
            metadata["file_path"] = str(final_path)
            metadata["expires_at"] = None  # Completed files don't expire
            await asyncio.to_thread(self._save_metadata, upload_id, metadata)

        return str(final_path)

    def _move_file(self, src: Path, dst: Path) -> None:
        """Move file from src to dst."""
        src.rename(dst)

    async def delete(self, upload_id: str) -> None:
        """Delete an upload and its data.

        Args:
            upload_id: The upload identifier.
        """
        data_path = self._data_path(upload_id)
        meta_path = self._meta_path(upload_id)

        await asyncio.to_thread(self._delete_files, data_path, meta_path)

    def _delete_files(self, *paths: Path) -> None:
        """Delete files if they exist."""
        for path in paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass

    async def cleanup_expired(self) -> int:
        """Clean up expired uploads.

        Returns:
            Number of uploads cleaned up.
        """
        count = 0
        now = datetime.now()

        meta_files = await asyncio.to_thread(
            lambda: list(self._uploads_dir.glob("*.meta"))
        )

        for meta_path in meta_files:
            upload_id = meta_path.stem
            metadata = await asyncio.to_thread(self._load_metadata, upload_id)

            if metadata is None:
                continue

            info = self._metadata_to_info(metadata)

            # Delete if expired and not complete
            if info.expires_at and now > info.expires_at and not info.is_complete:
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

        data_path = self._data_path(upload_id)
        if info.file_path:
            # If completed, read from final location
            data_path = Path(info.file_path)

        return await asyncio.to_thread(self._read_chunk, data_path, offset, length)

    def _read_chunk(self, path: Path, offset: int, length: int) -> bytes:
        """Read a chunk from file."""
        with open(path, "rb") as f:
            f.seek(offset)
            return f.read(length)
