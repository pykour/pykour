"""Configuration for file upload modules.

This module provides configuration classes for upload protocols and storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pykour.upload.storage.base import UploadStorage


@dataclass
class TusConfig:
    """Configuration for tus protocol middleware.

    Attributes:
        storage: Storage backend for upload data.
        path_prefix: URL path prefix for tus endpoints (e.g., "/files").
        max_size: Maximum upload size in bytes.
        expiration: Seconds until incomplete uploads expire.
        allow_empty_files: Whether to allow zero-byte uploads.
        cors_enabled: Whether to add CORS headers.
        cors_origins: Allowed CORS origins (default: all).
        cors_max_age: CORS preflight cache duration in seconds.

    Example:
        from pykour.upload import TusConfig, FileUploadStorage

        config = TusConfig(
            storage=FileUploadStorage(base_dir="./uploads"),
            path_prefix="/files",
            max_size=100 * 1024 * 1024,  # 100MB
            expiration=3600,  # 1 hour
        )
    """

    storage: "UploadStorage"
    path_prefix: str = "/files"
    max_size: int = 1024 * 1024 * 1024  # 1GB
    expiration: int = 86400  # 24 hours
    allow_empty_files: bool = True
    cors_enabled: bool = True
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    cors_max_age: int = 86400  # 24 hours

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Ensure path_prefix starts with /
        if not self.path_prefix.startswith("/"):
            self.path_prefix = "/" + self.path_prefix

        # Remove trailing slash
        self.path_prefix = self.path_prefix.rstrip("/")

        # Validate max_size
        if self.max_size <= 0:
            raise ValueError("max_size must be positive")

        # Validate expiration
        if self.expiration <= 0:
            raise ValueError("expiration must be positive")
