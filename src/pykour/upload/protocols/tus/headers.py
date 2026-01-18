"""tus protocol header definitions and parsing utilities.

This module defines the standard tus protocol headers and provides
utilities for parsing and validating them.

Headers defined by tus v1.0.0:
- Tus-Resumable: Protocol version (required for all requests)
- Tus-Version: Supported versions (server response)
- Tus-Extension: Supported extensions (server response)
- Tus-Max-Size: Maximum upload size (server response)
- Upload-Length: Total upload size (client request)
- Upload-Offset: Current offset (client/server)
- Upload-Metadata: File metadata (client request)
- Upload-Defer-Length: Defer length specification (client request)
"""

from __future__ import annotations

import base64
from dataclasses import dataclass

# tus protocol version
TUS_VERSION = "1.0.0"

# Supported tus versions (in order of preference)
TUS_SUPPORTED_VERSIONS = ["1.0.0"]

# Supported extensions
TUS_EXTENSIONS = ["creation", "termination", "expiration"]

# Header names
TUS_RESUMABLE_HEADER = "Tus-Resumable"
TUS_VERSION_HEADER = "Tus-Version"
TUS_EXTENSION_HEADER = "Tus-Extension"
TUS_MAX_SIZE_HEADER = "Tus-Max-Size"
UPLOAD_LENGTH_HEADER = "Upload-Length"
UPLOAD_OFFSET_HEADER = "Upload-Offset"
UPLOAD_METADATA_HEADER = "Upload-Metadata"
UPLOAD_DEFER_LENGTH_HEADER = "Upload-Defer-Length"
CONTENT_TYPE_HEADER = "Content-Type"
LOCATION_HEADER = "Location"

# Required content type for PATCH requests
TUS_CONTENT_TYPE = "application/offset+octet-stream"


@dataclass
class TusHeaders:
    """Parsed tus protocol headers.

    Attributes:
        tus_resumable: Client's tus version (from Tus-Resumable header).
        upload_length: Total size of the upload in bytes.
        upload_offset: Current upload offset.
        upload_metadata: Parsed metadata from Upload-Metadata header.
        upload_defer_length: Whether length is deferred.
        content_type: Content-Type of the request body.
        content_length: Content-Length of the request body.
    """

    tus_resumable: str | None = None
    upload_length: int | None = None
    upload_offset: int | None = None
    upload_metadata: dict[str, str] | None = None
    upload_defer_length: bool = False
    content_type: str | None = None
    content_length: int | None = None

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> "TusHeaders":
        """Parse tus headers from request headers dict.

        Args:
            headers: Request headers as a dictionary.

        Returns:
            TusHeaders with parsed values.

        Example:
            headers = {
                "Tus-Resumable": "1.0.0",
                "Upload-Length": "1000",
                "Upload-Metadata": "filename dGVzdC50eHQ=",
            }
            tus_headers = TusHeaders.from_headers(headers)
        """
        # Normalize header names to case-insensitive lookup
        normalized = {k.lower(): v for k, v in headers.items()}

        tus_resumable = normalized.get("tus-resumable")
        upload_length = _parse_int(normalized.get("upload-length"))
        upload_offset = _parse_int(normalized.get("upload-offset"))
        upload_defer_length = normalized.get("upload-defer-length") == "1"
        content_type = normalized.get("content-type")
        content_length = _parse_int(normalized.get("content-length"))

        # Parse metadata
        upload_metadata = None
        metadata_str = normalized.get("upload-metadata")
        if metadata_str:
            upload_metadata = parse_metadata(metadata_str)

        return cls(
            tus_resumable=tus_resumable,
            upload_length=upload_length,
            upload_offset=upload_offset,
            upload_metadata=upload_metadata,
            upload_defer_length=upload_defer_length,
            content_type=content_type,
            content_length=content_length,
        )

    def validate_version(self) -> bool:
        """Check if the tus version is supported.

        Returns:
            True if version is supported, False otherwise.
        """
        return self.tus_resumable in TUS_SUPPORTED_VERSIONS


def _parse_int(value: str | None) -> int | None:
    """Parse an integer from string, returning None if invalid."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def parse_metadata(metadata_str: str) -> dict[str, str]:
    """Parse Upload-Metadata header value.

    The Upload-Metadata header contains key-value pairs where:
    - Keys are ASCII strings
    - Values are Base64-encoded strings
    - Pairs are comma-separated
    - Key and value are space-separated

    Example:
        "filename dGVzdC50eHQ=,mimetype dGV4dC9wbGFpbg=="
        ->
        {"filename": "test.txt", "mimetype": "text/plain"}

    Args:
        metadata_str: Raw Upload-Metadata header value.

    Returns:
        Dictionary of decoded key-value pairs.
    """
    result: dict[str, str] = {}

    if not metadata_str:
        return result

    for pair in metadata_str.split(","):
        pair = pair.strip()
        if not pair:
            continue

        # Split on first space
        parts = pair.split(" ", 1)
        key = parts[0].strip()

        if len(parts) == 2:
            # Has a value - decode from Base64
            try:
                value = base64.b64decode(parts[1].strip()).decode("utf-8")
            except Exception:
                # Invalid Base64, use empty string
                value = ""
        else:
            # Key only, no value
            value = ""

        result[key] = value

    return result


def encode_metadata(metadata: dict[str, str]) -> str:
    """Encode metadata dictionary to Upload-Metadata header value.

    Args:
        metadata: Dictionary of key-value pairs.

    Returns:
        Formatted Upload-Metadata header value.

    Example:
        {"filename": "test.txt", "mimetype": "text/plain"}
        ->
        "filename dGVzdC50eHQ=,mimetype dGV4dC9wbGFpbg=="
    """
    pairs: list[str] = []

    for key, value in metadata.items():
        if value:
            encoded = base64.b64encode(value.encode("utf-8")).decode("ascii")
            pairs.append(f"{key} {encoded}")
        else:
            pairs.append(key)

    return ",".join(pairs)


def build_server_headers(
    upload_offset: int | None = None,
    upload_length: int | None = None,
    location: str | None = None,
    max_size: int | None = None,
    include_options: bool = False,
) -> dict[str, str]:
    """Build standard tus response headers.

    Args:
        upload_offset: Current upload offset.
        upload_length: Total upload length.
        location: Location URL for created uploads.
        max_size: Maximum upload size.
        include_options: Include headers for OPTIONS response.

    Returns:
        Dictionary of response headers.
    """
    headers: dict[str, str] = {
        TUS_RESUMABLE_HEADER: TUS_VERSION,
    }

    if include_options:
        headers[TUS_VERSION_HEADER] = ",".join(TUS_SUPPORTED_VERSIONS)
        headers[TUS_EXTENSION_HEADER] = ",".join(TUS_EXTENSIONS)
        if max_size is not None:
            headers[TUS_MAX_SIZE_HEADER] = str(max_size)

    if upload_offset is not None:
        headers[UPLOAD_OFFSET_HEADER] = str(upload_offset)

    if upload_length is not None:
        headers[UPLOAD_LENGTH_HEADER] = str(upload_length)

    if location is not None:
        headers[LOCATION_HEADER] = location

    return headers
