"""Conditional request decorators for ETag and Last-Modified support."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, TypeVar

# Registry attribute names for conditional request metadata
ETAG_REGISTRY_ATTR = "__pykour_etag__"
LAST_MODIFIED_REGISTRY_ATTR = "__pykour_last_modified__"

F = TypeVar("F", bound=Callable[..., object])


@dataclass
class ETagInfo:
    """ETag decorator metadata.

    Attributes:
        weak: If True, generate weak ETag (W/"...").
        algorithm: Hash algorithm ("md5", "sha1", "sha256"). Default: "md5".
    """

    weak: bool = False
    algorithm: str = "md5"


@dataclass
class LastModifiedInfo:
    """Last-Modified decorator metadata.

    Attributes:
        static_value: Fixed datetime value.
        response_field: Field name in response body (e.g., "updated_at").
        format: Date format string for parsing response field.
    """

    static_value: datetime | None = None
    response_field: str | None = None
    format: str = "%Y-%m-%dT%H:%M:%S"


def etag(
    *,
    weak: bool = False,
    algorithm: str = "md5",
) -> Callable[[F], F]:
    """Decorator to enable ETag support for handler responses.

    Automatically generates ETag from response body hash.
    Handles If-None-Match header and returns 304 Not Modified if matched.

    Args:
        weak: Generate weak ETag (W/"...") instead of strong ETag.
        algorithm: Hash algorithm ("md5", "sha1", "sha256").

    Returns:
        Decorator function.

    Example:
        @etag()
        async def get(request: Request, id: int = Path()) -> JSONResponse:
            return JSONResponse({"id": id, "data": "..."})

        # With weak ETag and SHA-256
        @etag(weak=True, algorithm="sha256")
        async def get_resource(request: Request) -> JSONResponse:
            return JSONResponse({"resource": "data"})
    """

    def decorator(func: F) -> F:
        if not hasattr(func, ETAG_REGISTRY_ATTR):
            setattr(func, ETAG_REGISTRY_ATTR, [])

        getattr(func, ETAG_REGISTRY_ATTR).append(
            ETagInfo(weak=weak, algorithm=algorithm)
        )
        return func

    return decorator


def last_modified(
    *,
    value: datetime | None = None,
    field: str | None = None,
    format: str = "%Y-%m-%dT%H:%M:%S",
) -> Callable[[F], F]:
    """Decorator to enable Last-Modified support for handler responses.

    Handles If-Modified-Since header and returns 304 Not Modified if not modified.

    Args:
        value: Fixed datetime value for Last-Modified header.
        field: Field name in response body to extract timestamp from.
               Supports dot notation (e.g., "metadata.updated_at").
        format: Date format string for parsing response field value.

    Returns:
        Decorator function.

    Example:
        # Fixed Last-Modified
        @last_modified(value=datetime(2024, 1, 1, 0, 0, 0))
        async def get_static(request: Request) -> JSONResponse:
            return JSONResponse({"data": "static content"})

        # Dynamic from response body
        @last_modified(field="updated_at")
        async def get_user(request: Request, id: int = Path()) -> JSONResponse:
            user = await get_user_from_db(id)
            return JSONResponse({
                "id": user.id,
                "name": user.name,
                "updated_at": user.updated_at.isoformat(),
            })

        # Nested field
        @last_modified(field="metadata.modified")
        async def get_item(request: Request) -> JSONResponse:
            return JSONResponse({
                "data": "...",
                "metadata": {"modified": "2024-01-15T10:30:00"}
            })
    """

    def decorator(func: F) -> F:
        if not hasattr(func, LAST_MODIFIED_REGISTRY_ATTR):
            setattr(func, LAST_MODIFIED_REGISTRY_ATTR, [])

        getattr(func, LAST_MODIFIED_REGISTRY_ATTR).append(
            LastModifiedInfo(
                static_value=value,
                response_field=field,
                format=format,
            )
        )
        return func

    return decorator


def get_etag_info(func: Callable[..., object]) -> list[ETagInfo]:
    """Get ETag metadata from a function.

    Args:
        func: Function to inspect.

    Returns:
        List of ETagInfo metadata, or empty list if not decorated.
    """
    return getattr(func, ETAG_REGISTRY_ATTR, [])


def get_last_modified_info(func: Callable[..., object]) -> list[LastModifiedInfo]:
    """Get Last-Modified metadata from a function.

    Args:
        func: Function to inspect.

    Returns:
        List of LastModifiedInfo metadata, or empty list if not decorated.
    """
    return getattr(func, LAST_MODIFIED_REGISTRY_ATTR, [])
