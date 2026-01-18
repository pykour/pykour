"""tus protocol implementation for resumable uploads.

The tus protocol (https://tus.io) provides a standardized way to
implement resumable file uploads over HTTP.

This module implements tus v1.0.0 with the following extensions:
- creation: Create new uploads with POST
- termination: Cancel uploads with DELETE
- expiration: Automatic cleanup of incomplete uploads
"""

from pykour.upload.protocols.tus.exceptions import (
    TusError,
    TusInvalidHeader,
    TusInvalidOffset,
    TusInvalidRequest,
    TusNotFound,
    TusSizeLimitExceeded,
    TusUnsupportedVersion,
    TusUploadExpired,
    TusUploadIncomplete,
)
from pykour.upload.protocols.tus.headers import (
    TUS_EXTENSIONS,
    TUS_MAX_SIZE_HEADER,
    TUS_VERSION,
    TusHeaders,
    parse_metadata,
)
from pykour.upload.protocols.tus.protocol import TusProtocol

__all__ = [
    # Protocol
    "TusProtocol",
    # Headers
    "TusHeaders",
    "parse_metadata",
    "TUS_VERSION",
    "TUS_EXTENSIONS",
    "TUS_MAX_SIZE_HEADER",
    # Exceptions
    "TusError",
    "TusInvalidHeader",
    "TusInvalidOffset",
    "TusInvalidRequest",
    "TusNotFound",
    "TusSizeLimitExceeded",
    "TusUnsupportedVersion",
    "TusUploadExpired",
    "TusUploadIncomplete",
]
