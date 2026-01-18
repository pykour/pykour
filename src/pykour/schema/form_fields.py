"""Form and file field markers for multipart/form-data."""

from __future__ import annotations

from typing import Any, Callable

from pykour.schema.fields import MISSING, FieldInfo


class Form(FieldInfo):
    """Marker for form text fields from multipart/form-data.

    Use this to annotate handler parameters that should be extracted
    from form fields in a multipart/form-data request.

    Example:
        async def post(
            username: str = Form(),
            email: str = Form(default=""),
        ):
            return {"username": username, "email": email}

        # With alias for different form field name
        async def post(
            user_name: str = Form(alias="username"),
        ):
            return {"user_name": user_name}
    """

    def __init__(
        self,
        default: Any = MISSING,
        *,
        default_factory: Callable[[], Any] | None = None,
        alias: str | None = None,
        description: str | None = None,
        media_type: str = "application/x-www-form-urlencoded",
    ) -> None:
        """Initialize Form marker.

        Args:
            default: Default value if field is not provided.
            default_factory: Factory function for default value.
            alias: Alternative field name in the form data.
            description: Description for OpenAPI documentation.
            media_type: Expected media type for the form data.
        """
        super().__init__(
            default=default,
            default_factory=default_factory,
            alias=alias,
            description=description,
        )
        self.media_type = media_type


class File(FieldInfo):
    """Marker for file uploads from multipart/form-data.

    Use this to annotate handler parameters that should receive
    uploaded files from a multipart/form-data request.

    Example:
        # Single file upload
        async def post(avatar: UploadFile = File()):
            content = await avatar.read()
            return {"filename": avatar.filename, "size": len(content)}

        # Multiple file upload
        async def post(documents: list[UploadFile] = File()):
            return {"count": len(documents)}

        # With validation constraints
        async def post(
            image: UploadFile = File(
                max_size=5 * 1024 * 1024,  # 5MB max
                allowed_types=["image/jpeg", "image/png"],
            )
        ):
            ...
    """

    def __init__(
        self,
        default: Any = MISSING,
        *,
        default_factory: Callable[[], Any] | None = None,
        alias: str | None = None,
        description: str | None = None,
        max_size: int | None = None,
        allowed_types: list[str] | None = None,
    ) -> None:
        """Initialize File marker.

        Args:
            default: Default value if file is not provided.
            default_factory: Factory function for default value.
            alias: Alternative field name in the form data.
            description: Description for OpenAPI documentation.
            max_size: Maximum file size in bytes.
            allowed_types: List of allowed MIME types.
        """
        super().__init__(
            default=default,
            default_factory=default_factory,
            alias=alias,
            description=description,
        )
        self.max_size = max_size
        self.allowed_types = allowed_types
