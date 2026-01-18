"""File upload module with protocol abstraction.

This module provides extensible file upload support with multiple protocols:
- Standard multipart/form-data uploads
- tus protocol for resumable uploads

Example:
    from pykour import Pykour
    from pykour.upload import TusMiddleware, FileUploadStorage

    app = Pykour()
    app.add_middleware(
        TusMiddleware,
        storage=FileUploadStorage(base_dir="./uploads"),
        path_prefix="/files",
    )
"""

from pykour.upload.config import TusConfig
from pykour.upload.middleware import TusMiddleware
from pykour.upload.protocols.base import UploadProtocol, UploadResult
from pykour.upload.protocols.tus import TusProtocol
from pykour.upload.storage.base import UploadInfo, UploadStorage
from pykour.upload.storage.file import FileUploadStorage
from pykour.upload.storage.memory import MemoryUploadStorage

__all__ = [
    # Protocols
    "UploadProtocol",
    "UploadResult",
    "TusProtocol",
    # Storage
    "UploadStorage",
    "UploadInfo",
    "FileUploadStorage",
    "MemoryUploadStorage",
    # Middleware
    "TusMiddleware",
    # Config
    "TusConfig",
]
