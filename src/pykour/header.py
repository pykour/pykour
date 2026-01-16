"""Header decorators for declarative HTTP response headers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

HEADER_REGISTRY_ATTR = "__pykour_headers__"

F = TypeVar("F", bound=Callable[..., object])


@dataclass
class HeaderInfo:
    """Header decorator metadata.

    Attributes:
        name: HTTP header name (e.g., "Location", "X-Request-Id").
        value_template: Value template with optional {param} placeholders.
        condition: Optional condition function that takes status code and returns bool.
    """

    name: str
    value_template: str
    condition: Callable[[int], bool] | None = None


def header(
    name: str,
    value: str,
    *,
    on_status: int | tuple[int, ...] | None = None,
) -> Callable[[F], F]:
    """Decorator to declare HTTP response headers.

    Headers are applied after the handler returns, allowing dynamic values
    based on path parameters, query parameters, or response body.

    Args:
        name: HTTP header name.
        value: Header value template. Use {param} for dynamic values.
               Parameters are resolved from handler kwargs first, then response body.
        on_status: Only apply header on specific status code(s).

    Returns:
        Decorator function.

    Examples:
        # Static header
        @header("X-API-Version", "1.0")
        async def get(request: Request) -> JSONResponse:
            return JSONResponse({"data": "value"})

        # Dynamic header from response body
        @header("Location", "/users/{id}")
        @status_code(201)
        async def post(request: Request) -> JSONResponse:
            return JSONResponse({"id": 123})  # Location: /users/123

        # Dynamic header from path parameter
        @header("Location", "/users/{user_id}")
        @status_code(201)
        async def create(request: Request, user_id: int = Path()) -> JSONResponse:
            return JSONResponse({"created": True})

        # Conditional header (only on 201)
        @header("Location", "/items/{id}", on_status=201)
        async def create_item(request: Request) -> JSONResponse:
            item = await create(...)
            return JSONResponse({"id": item.id}, status_code=201)

        # Multiple headers (stackable)
        @header("X-Request-Id", "{request_id}")
        @header("X-Correlation-Id", "{correlation_id}")
        async def handler(request: Request, request_id: str = Query()) -> JSONResponse:
            return JSONResponse({"ok": True})
    """

    def decorator(func: F) -> F:
        if not hasattr(func, HEADER_REGISTRY_ATTR):
            setattr(func, HEADER_REGISTRY_ATTR, [])

        # Build condition function from on_status
        condition: Callable[[int], bool] | None = None
        if on_status is not None:
            condition = _make_status_condition(on_status)

        getattr(func, HEADER_REGISTRY_ATTR).append(
            HeaderInfo(name=name, value_template=value, condition=condition)
        )
        return func

    return decorator


def _make_status_condition(
    on_status: int | tuple[int, ...],
) -> Callable[[int], bool]:
    """Create a condition function for status code checking.

    Args:
        on_status: Single status code or tuple of status codes.

    Returns:
        Condition function that checks if status matches.
    """
    if isinstance(on_status, int):

        def check_single(code: int) -> bool:
            return code == on_status

        return check_single
    else:
        statuses = on_status

        def check_multiple(code: int) -> bool:
            return code in statuses

        return check_multiple


def get_header_info(func: Callable[..., object]) -> list[HeaderInfo]:
    """Get header metadata from a function.

    Args:
        func: Function to inspect.

    Returns:
        List of HeaderInfo metadata, or empty list if none.
    """
    return getattr(func, HEADER_REGISTRY_ATTR, [])
