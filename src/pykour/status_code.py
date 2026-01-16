"""Status code decorators for declarative HTTP response codes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

STATUS_CODE_REGISTRY_ATTR = "__pykour_status_code__"

F = TypeVar("F", bound=Callable[..., object])


@dataclass
class StatusCodeInfo:
    """Status code decorator metadata.

    Attributes:
        code: HTTP status code (e.g., 200, 201, 204).
        description: Human-readable description for OpenAPI documentation.
        is_default: If True, this status code is applied when response uses default (200).
    """

    code: int
    description: str | None = None
    is_default: bool = True


def status_code(
    code: int,
    description: str | None = None,
    *,
    is_default: bool = True,
) -> Callable[[F], F]:
    """Decorator to declare default HTTP status code for handler responses.

    When a handler returns a Response with the default status code (200),
    the declaratively defined status code will be applied instead.

    If the handler explicitly sets a status code (e.g., JSONResponse(status_code=201)),
    the explicit value takes precedence over the declarative definition.

    Multiple @status_code decorators can be stacked for OpenAPI documentation
    purposes (to document multiple possible responses).

    Args:
        code: HTTP status code to use as default.
        description: Description for OpenAPI documentation.
        is_default: If True, apply this code when response has default status.
                    If False, only used for OpenAPI documentation.

    Returns:
        Decorator function.

    Example:
        @status_code(201, description="Created")
        async def post(request: Request, data: UserSchema = Body()) -> JSONResponse:
            user = await create_user(data)
            return JSONResponse({"id": user.id})

        # Multiple status codes for OpenAPI docs
        @status_code(200, description="Success")
        @status_code(404, description="Not Found", is_default=False)
        async def get(request: Request, id: int = Path()) -> JSONResponse:
            user = await get_user(id)
            if not user:
                return JSONResponse({"error": "Not found"}, status_code=404)
            return JSONResponse(user)
    """

    def decorator(func: F) -> F:
        if not hasattr(func, STATUS_CODE_REGISTRY_ATTR):
            setattr(func, STATUS_CODE_REGISTRY_ATTR, [])

        getattr(func, STATUS_CODE_REGISTRY_ATTR).append(
            StatusCodeInfo(code=code, description=description, is_default=is_default)
        )
        return func

    return decorator


def get_status_code_info(func: Callable[..., object]) -> list[StatusCodeInfo]:
    """Get status code metadata from a function.

    Args:
        func: Function to inspect.

    Returns:
        List of StatusCodeInfo metadata, or empty list if none.
    """
    return getattr(func, STATUS_CODE_REGISTRY_ATTR, [])


def get_default_status_code(func: Callable[..., object]) -> int | None:
    """Get the default status code for a handler.

    Returns the first StatusCodeInfo with is_default=True, or None if
    no default status code is declared.

    Args:
        func: Handler function to inspect.

    Returns:
        Default status code, or None.
    """
    infos = get_status_code_info(func)
    for info in infos:
        if info.is_default:
            return info.code
    return None


def get_method_default_status_code(method: str) -> int:
    """Get default status code for HTTP method when no decorator is present.

    This provides RESTful defaults:
    - POST: 201 (Created)
    - DELETE: 204 (No Content)
    - Others: 200 (OK)

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.).

    Returns:
        Default status code for the method.
    """
    defaults = {
        "POST": 201,
        "DELETE": 204,
    }
    return defaults.get(method.upper(), 200)
