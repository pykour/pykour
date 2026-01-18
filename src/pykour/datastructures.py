"""Data structures for file uploads and form data."""

from __future__ import annotations

import tempfile
from typing import IO, Any


class UploadFile:
    """Represents an uploaded file from multipart/form-data.

    FastAPI-compatible API for file uploads. Uses SpooledTemporaryFile
    internally to store small files in memory and larger files on disk.

    Attributes:
        filename: Original filename from the upload.
        content_type: MIME type of the uploaded file.
        headers: Additional headers from the multipart part.

    Example:
        async def post(avatar: UploadFile = File()):
            content = await avatar.read()
            return {"filename": avatar.filename, "size": len(content)}
    """

    spool_max_size: int = 1024 * 1024  # 1MB

    def __init__(
        self,
        file: IO[bytes],
        *,
        filename: str | None = None,
        content_type: str = "application/octet-stream",
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize an UploadFile instance.

        Args:
            file: File-like object containing the uploaded data.
            filename: Original filename from the upload.
            content_type: MIME type of the file.
            headers: Additional headers from the multipart part.
        """
        self.file = file
        self.filename = filename
        self.content_type = content_type
        self.headers = headers or {}
        self._size: int | None = None

    @property
    def size(self) -> int | None:
        """File size in bytes. Available after reading the entire file."""
        return self._size

    async def read(self, size: int = -1) -> bytes:
        """Read file content.

        Args:
            size: Number of bytes to read. -1 reads entire file.

        Returns:
            File content as bytes.
        """
        content = self.file.read(size)
        if size == -1:
            self._size = len(content)
        return content

    async def write(self, data: bytes) -> int:
        """Write data to the file.

        Args:
            data: Bytes to write.

        Returns:
            Number of bytes written.
        """
        return self.file.write(data)

    async def seek(self, offset: int, whence: int = 0) -> int:
        """Move file position.

        Args:
            offset: Position offset.
            whence: Reference point (0=start, 1=current, 2=end).

        Returns:
            New absolute position.
        """
        return self.file.seek(offset, whence)

    async def close(self) -> None:
        """Close the file."""
        self.file.close()

    @classmethod
    def _create_temp_file(cls) -> IO[bytes]:
        """Create a SpooledTemporaryFile for storing upload data.

        Returns:
            SpooledTemporaryFile instance.
        """
        return tempfile.SpooledTemporaryFile(max_size=cls.spool_max_size)

    def __repr__(self) -> str:
        return f"UploadFile(filename={self.filename!r}, content_type={self.content_type!r})"


class FormData:
    """Container for parsed multipart form data.

    Holds both text fields and uploaded files from a multipart/form-data
    request.

    Attributes:
        fields: Dictionary of text field values.
        files: Dictionary of uploaded files.
    """

    def __init__(
        self,
        fields: dict[str, str | list[str]] | None = None,
        files: dict[str, UploadFile | list[UploadFile]] | None = None,
    ) -> None:
        """Initialize FormData.

        Args:
            fields: Text field values.
            files: Uploaded files.
        """
        self._fields = fields or {}
        self._files = files or {}

    @property
    def fields(self) -> dict[str, str | list[str]]:
        """Text field values."""
        return self._fields

    @property
    def files(self) -> dict[str, UploadFile | list[UploadFile]]:
        """Uploaded files."""
        return self._files

    def get(self, key: str, default: Any = None) -> Any:
        """Get a field or file by key.

        Args:
            key: Field name.
            default: Default value if key not found.

        Returns:
            Field value, UploadFile, or default.
        """
        if key in self._fields:
            return self._fields[key]
        if key in self._files:
            return self._files[key]
        return default

    def __repr__(self) -> str:
        return f"FormData(fields={list(self._fields.keys())}, files={list(self._files.keys())})"
