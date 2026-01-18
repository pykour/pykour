"""Multipart form data parsing for file uploads."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

from pykour.datastructures import FormData, UploadFile
from pykour.schema.errors import ErrorDetail, ValidationError

if TYPE_CHECKING:
    from pykour.request import Request


def _add_to_dict(d: dict[str, Any], key: str, value: Any) -> None:
    """Add value to dict, converting to list if key exists."""
    if key in d:
        existing = d[key]
        if isinstance(existing, list):
            existing.append(value)
        else:
            d[key] = [existing, value]
    else:
        d[key] = value


async def parse_multipart(request: "Request") -> FormData:
    """Parse multipart/form-data request body.

    Uses python-multipart library for parsing.

    Args:
        request: Pykour Request instance.

    Returns:
        FormData containing parsed fields and files.

    Raises:
        ValidationError: If Content-Type is invalid or parsing fails.
        ImportError: If python-multipart is not installed.
    """
    try:
        import python_multipart
        from python_multipart.multipart import parse_options_header
    except ImportError as e:
        raise ImportError(
            "python-multipart is required for file uploads. "
            "Install it with: pip install python-multipart"
        ) from e

    content_type = request.headers.get("content-type", "")
    content_type_header, params = parse_options_header(content_type.encode())

    if content_type_header != b"multipart/form-data":
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("header", "content-type"),
                    msg=f"Expected multipart/form-data, got {content_type}",
                    type="value_error.content_type",
                )
            ]
        )

    boundary = params.get(b"boundary")
    if not boundary:
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("header", "content-type"),
                    msg="Missing boundary in Content-Type header",
                    type="value_error.boundary",
                )
            ]
        )

    fields: dict[str, str | list[str]] = {}
    files: dict[str, UploadFile | list[UploadFile]] = {}

    def on_field(field: Any) -> None:
        """Callback for text form fields."""
        field_name = field.field_name
        if isinstance(field_name, bytes):
            field_name = field_name.decode("utf-8", errors="replace")

        value = field.value
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")

        _add_to_dict(fields, field_name, value)

    def on_file(file: Any) -> None:
        """Callback for file uploads."""
        field_name = file.field_name
        if isinstance(field_name, bytes):
            field_name = field_name.decode("utf-8", errors="replace")

        filename = file.file_name
        if isinstance(filename, bytes):
            filename = filename.decode("utf-8", errors="replace")

        # python-multipart File object doesn't expose content_type
        # Default to application/octet-stream
        content_type_val = "application/octet-stream"

        # Create UploadFile from the file object
        temp_file = UploadFile._create_temp_file()

        # Copy file content to temp file
        file.file_object.seek(0)
        content = file.file_object.read()
        temp_file.write(content)
        temp_file.seek(0)

        upload_file = UploadFile(
            file=temp_file,
            filename=filename,
            content_type=content_type_val,
        )
        upload_file._size = len(content)

        _add_to_dict(files, field_name, upload_file)

    # Read body and create a file-like object for parsing
    body = await request.body()
    body_file = io.BytesIO(body)

    # Create headers dict for python-multipart (str keys, str values)
    headers: dict[str, str] = {"Content-Type": content_type}
    content_length = request.headers.get("content-length")
    if content_length:
        headers["Content-Length"] = content_length

    try:
        python_multipart.parse_form(headers, body_file, on_field, on_file)  # type: ignore[arg-type]
    except Exception as e:
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("body",),
                    msg=f"Failed to parse multipart data: {e}",
                    type="value_error.parse_error",
                )
            ]
        ) from e

    return FormData(fields=fields, files=files)


async def parse_urlencoded(request: "Request") -> FormData:
    """Parse application/x-www-form-urlencoded request body.

    Args:
        request: Pykour Request instance.

    Returns:
        FormData containing parsed fields (no files).

    Raises:
        ValidationError: If parsing fails.
    """
    body = await request.body()

    try:
        parsed = parse_qs(
            body.decode("utf-8", errors="replace"),
            keep_blank_values=True,
        )
    except Exception as e:
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("body",),
                    msg=f"Failed to parse form data: {e}",
                    type="value_error.parse_error",
                )
            ]
        ) from e

    # Convert lists to single values where appropriate
    fields: dict[str, str | list[str]] = {}
    for key, values in parsed.items():
        if len(values) == 1:
            fields[key] = values[0]
        else:
            fields[key] = values

    return FormData(fields=fields, files={})
