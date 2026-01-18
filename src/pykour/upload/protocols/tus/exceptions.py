"""tus protocol specific exceptions.

This module defines exceptions for tus protocol error conditions.
Each exception maps to a specific HTTP status code and error message.
"""

from __future__ import annotations


class TusError(Exception):
    """Base exception for tus protocol errors.

    Attributes:
        message: Human-readable error message.
        status_code: HTTP status code to return.
    """

    message: str = "An error occurred"
    status_code: int = 500

    def __init__(self, message: str | None = None) -> None:
        """Initialize with optional custom message.

        Args:
            message: Optional custom error message.
        """
        self.message = message or self.__class__.message
        super().__init__(self.message)


class TusUnsupportedVersion(TusError):
    """Client requested an unsupported tus protocol version.

    HTTP Status: 412 Precondition Failed
    """

    message = "Unsupported tus protocol version"
    status_code = 412


class TusInvalidHeader(TusError):
    """A required header is missing or invalid.

    HTTP Status: 400 Bad Request
    """

    message = "Invalid or missing header"
    status_code = 400


class TusInvalidRequest(TusError):
    """The request is malformed or invalid.

    HTTP Status: 400 Bad Request
    """

    message = "Invalid request"
    status_code = 400


class TusInvalidOffset(TusError):
    """The Upload-Offset header doesn't match the current offset.

    HTTP Status: 409 Conflict
    """

    message = "Offset mismatch"
    status_code = 409


class TusNotFound(TusError):
    """The requested upload was not found.

    HTTP Status: 404 Not Found
    """

    message = "Upload not found"
    status_code = 404


class TusSizeLimitExceeded(TusError):
    """The upload exceeds the maximum allowed size.

    HTTP Status: 413 Payload Too Large
    """

    message = "Upload exceeds maximum size"
    status_code = 413


class TusUploadExpired(TusError):
    """The upload has expired and is no longer available.

    HTTP Status: 410 Gone
    """

    message = "Upload has expired"
    status_code = 410


class TusUploadIncomplete(TusError):
    """The upload is not yet complete.

    HTTP Status: 400 Bad Request
    """

    message = "Upload is incomplete"
    status_code = 400


class TusChecksumMismatch(TusError):
    """The uploaded data doesn't match the provided checksum.

    HTTP Status: 460 Checksum Mismatch (tus-specific)
    """

    message = "Checksum mismatch"
    status_code = 460
