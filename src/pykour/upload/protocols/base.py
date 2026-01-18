"""Base protocol abstraction for file uploads.

This module defines the abstract interface for upload protocols,
allowing different upload mechanisms (multipart, tus, etc.) to be
implemented with a consistent API.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pykour.request import Request


@dataclass
class UploadResult:
    """Result of a file upload operation.

    Attributes:
        upload_id: Unique identifier for the upload.
        filename: Original filename from the client.
        content_type: MIME type of the uploaded file.
        size: Size of the uploaded file in bytes.
        offset: Current offset for resumable uploads (0 for complete uploads).
        is_complete: Whether the upload is complete.
        metadata: Additional metadata from the upload.
        file_path: Path to the uploaded file (if stored to filesystem).
    """

    upload_id: str
    filename: str | None = None
    content_type: str = "application/octet-stream"
    size: int = 0
    offset: int = 0
    is_complete: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    file_path: str | None = None


class UploadProtocol(ABC):
    """Abstract base class for upload protocols.

    This class defines the interface that all upload protocols must implement.
    Each protocol handles a specific upload mechanism (multipart, tus, etc.).

    Example:
        class CustomProtocol(UploadProtocol):
            @property
            def name(self) -> str:
                return "custom"

            def can_handle(self, request: Request) -> bool:
                return "X-Custom-Upload" in request.headers

            async def handle(self, request: Request) -> UploadResult:
                # Handle the upload
                ...
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Protocol name for identification.

        Returns:
            A unique string identifier for this protocol.
        """
        ...

    @abstractmethod
    def can_handle(self, request: "Request") -> bool:
        """Check if this protocol can handle the given request.

        Args:
            request: The incoming HTTP request.

        Returns:
            True if this protocol should handle the request.
        """
        ...

    @abstractmethod
    async def handle(self, request: "Request") -> UploadResult:
        """Handle the upload request.

        Args:
            request: The incoming HTTP request.

        Returns:
            UploadResult containing information about the upload.

        Raises:
            ValidationError: If the request is malformed.
            UploadError: If the upload fails.
        """
        ...
