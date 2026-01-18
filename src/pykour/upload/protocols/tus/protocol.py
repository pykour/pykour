"""tus protocol implementation.

This module provides the main TusProtocol class that coordinates
all tus protocol operations.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pykour.upload.protocols.base import UploadProtocol, UploadResult
from pykour.upload.protocols.tus.exceptions import (
    TusInvalidHeader,
    TusInvalidOffset,
    TusNotFound,
    TusSizeLimitExceeded,
    TusUnsupportedVersion,
)
from pykour.upload.protocols.tus.headers import (
    TUS_CONTENT_TYPE,
    TUS_VERSION,
    TusHeaders,
    build_server_headers,
)

if TYPE_CHECKING:
    from pykour.request import Request
    from pykour.upload.storage.base import UploadStorage


class TusProtocol(UploadProtocol):
    """tus protocol (v1.0.0) implementation.

    This class handles all tus protocol operations including:
    - OPTIONS: Server capability discovery
    - POST: Create new upload
    - HEAD: Get upload status
    - PATCH: Upload chunk
    - DELETE: Cancel upload

    Example:
        from pykour.upload.protocols.tus import TusProtocol
        from pykour.upload.storage import MemoryUploadStorage

        storage = MemoryUploadStorage()
        protocol = TusProtocol(storage, max_size=100 * 1024 * 1024)

        # Handle OPTIONS request
        headers = protocol.get_options_headers()

        # Create upload
        result = await protocol.create_upload(request)

        # Get upload status
        info = await protocol.get_upload_status(upload_id)

        # Write chunk
        result = await protocol.write_chunk(upload_id, request)
    """

    def __init__(
        self,
        storage: "UploadStorage",
        max_size: int = 1024 * 1024 * 1024,  # 1GB
        path_prefix: str = "/files",
    ) -> None:
        """Initialize tus protocol handler.

        Args:
            storage: Storage backend for upload data.
            max_size: Maximum upload size in bytes.
            path_prefix: URL path prefix for upload endpoints.
        """
        self._storage = storage
        self._max_size = max_size
        self._path_prefix = path_prefix.rstrip("/")

    @property
    def name(self) -> str:
        """Protocol name for identification."""
        return "tus"

    @property
    def storage(self) -> "UploadStorage":
        """Get the storage backend."""
        return self._storage

    @property
    def max_size(self) -> int:
        """Get the maximum upload size."""
        return self._max_size

    @property
    def path_prefix(self) -> str:
        """Get the URL path prefix."""
        return self._path_prefix

    def can_handle(self, request: "Request") -> bool:
        """Check if this protocol can handle the given request.

        A request is handled by tus if:
        - The path starts with the configured path_prefix
        - The Tus-Resumable header is present (except for OPTIONS)

        Args:
            request: The incoming HTTP request.

        Returns:
            True if this protocol should handle the request.
        """
        if not request.path.startswith(self._path_prefix):
            return False

        # OPTIONS doesn't require Tus-Resumable header
        if request.method == "OPTIONS":
            return True

        # Other methods require Tus-Resumable header
        return "tus-resumable" in {k.lower() for k in request.headers.keys()}

    async def handle(self, request: "Request") -> UploadResult:
        """Handle a tus protocol request.

        This method dispatches to the appropriate handler based on
        the HTTP method.

        Args:
            request: The incoming HTTP request.

        Returns:
            UploadResult for the operation.

        Raises:
            TusError: If the request fails validation or processing.
        """
        method = request.method.upper()

        if method == "POST":
            return await self.create_upload(request)
        elif method == "HEAD":
            upload_id = self._extract_upload_id(request.path)
            return await self.get_upload_status(upload_id)
        elif method == "PATCH":
            upload_id = self._extract_upload_id(request.path)
            return await self.write_chunk(upload_id, request)
        elif method == "DELETE":
            upload_id = self._extract_upload_id(request.path)
            return await self.delete_upload(upload_id)
        else:
            # Should not reach here if can_handle is correct
            raise TusInvalidHeader(f"Unsupported method: {method}")

    def _extract_upload_id(self, path: str) -> str:
        """Extract upload ID from request path.

        Args:
            path: Request path like "/files/abc123".

        Returns:
            Upload ID extracted from path.

        Raises:
            TusInvalidHeader: If upload ID is missing.
        """
        # Remove path prefix
        suffix = path[len(self._path_prefix) :].lstrip("/")
        if not suffix:
            raise TusInvalidHeader("Upload ID required")
        return suffix.split("/")[0]

    def _validate_version(self, headers: TusHeaders) -> None:
        """Validate tus protocol version.

        Args:
            headers: Parsed tus headers.

        Raises:
            TusUnsupportedVersion: If version is not supported.
        """
        if not headers.validate_version():
            raise TusUnsupportedVersion(
                f"Unsupported version: {headers.tus_resumable}. "
                f"Supported: {TUS_VERSION}"
            )

    def get_options_headers(self) -> dict[str, str]:
        """Get response headers for OPTIONS request.

        Returns:
            Dictionary of response headers.
        """
        return build_server_headers(
            max_size=self._max_size,
            include_options=True,
        )

    async def create_upload(self, request: "Request") -> UploadResult:
        """Create a new upload (POST handler).

        Args:
            request: The incoming HTTP request.

        Returns:
            UploadResult with the created upload information.

        Raises:
            TusError: If creation fails.
        """
        headers = TusHeaders.from_headers(request.headers)
        self._validate_version(headers)

        # Get upload length
        upload_length = headers.upload_length
        if upload_length is None and not headers.upload_defer_length:
            raise TusInvalidHeader("Upload-Length header required")

        # Check size limit
        if upload_length is not None and upload_length > self._max_size:
            raise TusSizeLimitExceeded(
                f"Upload size {upload_length} exceeds maximum {self._max_size}"
            )

        # Generate upload ID
        upload_id = str(uuid.uuid4())

        # Extract metadata
        metadata = headers.upload_metadata or {}
        filename = metadata.get("filename")
        content_type = metadata.get("contentType", "application/octet-stream")

        # Create upload in storage
        info = await self._storage.create(
            upload_id=upload_id,
            size=upload_length or 0,
            metadata={
                "filename": filename,
                "content_type": content_type,
                **metadata,
            },
        )

        return UploadResult(
            upload_id=upload_id,
            filename=filename,
            content_type=content_type,
            size=info.size,
            offset=0,
            is_complete=False,
            metadata=metadata,
        )

    async def get_upload_status(self, upload_id: str) -> UploadResult:
        """Get upload status (HEAD handler).

        Args:
            upload_id: The upload identifier.

        Returns:
            UploadResult with current status.

        Raises:
            TusNotFound: If upload doesn't exist.
        """
        info = await self._storage.get_info(upload_id)
        if info is None:
            raise TusNotFound(f"Upload {upload_id} not found")

        return UploadResult(
            upload_id=upload_id,
            filename=info.filename,
            content_type=info.content_type,
            size=info.size,
            offset=info.offset,
            is_complete=info.is_complete,
            metadata=info.metadata,
            file_path=info.file_path,
        )

    async def write_chunk(self, upload_id: str, request: "Request") -> UploadResult:
        """Write a chunk of data (PATCH handler).

        Args:
            upload_id: The upload identifier.
            request: The incoming HTTP request with chunk data.

        Returns:
            UploadResult with updated status.

        Raises:
            TusError: If write fails.
        """
        headers = TusHeaders.from_headers(request.headers)
        self._validate_version(headers)

        # Validate Content-Type
        if headers.content_type != TUS_CONTENT_TYPE:
            raise TusInvalidHeader(
                f"Content-Type must be {TUS_CONTENT_TYPE}, got {headers.content_type}"
            )

        # Validate Upload-Offset
        if headers.upload_offset is None:
            raise TusInvalidHeader("Upload-Offset header required")

        # Get current upload info
        info = await self._storage.get_info(upload_id)
        if info is None:
            raise TusNotFound(f"Upload {upload_id} not found")

        # Check offset matches
        if headers.upload_offset != info.offset:
            raise TusInvalidOffset(
                f"Offset mismatch: expected {info.offset}, got {headers.upload_offset}"
            )

        # Read and write chunk data
        body = await request.body()
        new_offset = await self._storage.write_chunk(
            upload_id=upload_id,
            offset=info.offset,
            data=body,
        )

        # Check if upload is complete
        is_complete = new_offset >= info.size
        file_path = None
        if is_complete:
            file_path = await self._storage.complete(upload_id)

        return UploadResult(
            upload_id=upload_id,
            filename=info.filename,
            content_type=info.content_type,
            size=info.size,
            offset=new_offset,
            is_complete=is_complete,
            metadata=info.metadata,
            file_path=file_path,
        )

    async def delete_upload(self, upload_id: str) -> UploadResult:
        """Delete/cancel an upload (DELETE handler).

        Args:
            upload_id: The upload identifier.

        Returns:
            UploadResult with deleted status.

        Raises:
            TusNotFound: If upload doesn't exist.
        """
        info = await self._storage.get_info(upload_id)
        if info is None:
            raise TusNotFound(f"Upload {upload_id} not found")

        await self._storage.delete(upload_id)

        return UploadResult(
            upload_id=upload_id,
            filename=info.filename,
            content_type=info.content_type,
            size=info.size,
            offset=info.offset,
            is_complete=False,
            metadata=info.metadata,
        )

    def build_location_url(self, upload_id: str, base_url: str = "") -> str:
        """Build the Location URL for a created upload.

        Args:
            upload_id: The upload identifier.
            base_url: Optional base URL (scheme + host).

        Returns:
            Full URL to the upload resource.
        """
        return f"{base_url}{self._path_prefix}/{upload_id}"
