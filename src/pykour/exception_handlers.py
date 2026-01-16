"""Exception handler registry for Pykour.

This module provides a registry for mapping exception types to handler functions.
Handlers are looked up using the exception's Method Resolution Order (MRO),
allowing subclass exceptions to be caught by parent class handlers.

Example:
    registry = ExceptionHandlerRegistry()

    async def handle_not_found(request, exc):
        return JSONResponse({"error": exc.detail}, status_code=404)

    registry.add(NotFoundException, handle_not_found)

    # Later, when an exception is caught:
    handler = registry.get(exc)
    if handler:
        response = await handler(request, exc)
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from pykour.request import Request
    from pykour.response import Response

# Type alias for exception handler functions
# Handlers can be sync or async, must accept (Request, Exception) and return Response
# Using Any for exception type to allow handlers with more specific exception types
ExceptionHandler = Callable[["Request", Any], Union[Awaitable["Response"], "Response"]]


class ExceptionHandlerRegistry:
    """Registry for mapping exception types to handler functions.

    Handlers are looked up by walking the exception's MRO (Method Resolution Order),
    so a handler registered for a parent exception class will also handle its
    subclasses unless a more specific handler is registered.

    Example:
        registry = ExceptionHandlerRegistry()

        # Register handler for base HTTPException
        registry.add(HTTPException, default_http_handler)

        # Register more specific handler for NotFoundException
        registry.add(NotFoundException, not_found_handler)

        # ItemNotFoundException (subclass of NotFoundException) will be handled
        # by not_found_handler, not default_http_handler
    """

    def __init__(self) -> None:
        """Initialize an empty exception handler registry."""
        self._handlers: dict[type[Any], ExceptionHandler] = {}

    def add(
        self,
        exc_class: type[Exception],
        handler: ExceptionHandler,
    ) -> None:
        """Register an exception handler for a specific exception type.

        Args:
            exc_class: The exception class to handle.
            handler: A callable that accepts (Request, Exception) and returns a Response.
                Can be async or sync.

        Example:
            async def handle_value_error(request, exc):
                return JSONResponse({"error": str(exc)}, status_code=400)

            registry.add(ValueError, handle_value_error)
        """
        self._handlers[exc_class] = handler

    def get(self, exc: Exception) -> ExceptionHandler | None:
        """Get the handler for an exception, checking the MRO.

        Walks through the exception's Method Resolution Order to find
        the most specific handler available. This means a handler for
        a parent class will catch subclass exceptions.

        Args:
            exc: The exception instance to find a handler for.

        Returns:
            The handler function if found, None otherwise.

        Example:
            # If NotFoundExceptionis registered and ItemNotFoundException
            # (subclass) is raised, the NotFoundExceptionhandler is returned.
            handler = registry.get(ItemNotFoundException("item not found"))
        """
        for cls in type(exc).__mro__:
            if cls in self._handlers:
                return self._handlers[cls]
        return None

    def remove(self, exc_class: type[Exception]) -> bool:
        """Remove a handler for a specific exception type.

        Args:
            exc_class: The exception class to remove the handler for.

        Returns:
            True if a handler was removed, False if no handler existed.
        """
        if exc_class in self._handlers:
            del self._handlers[exc_class]
            return True
        return False

    def clear(self) -> None:
        """Remove all registered handlers."""
        self._handlers.clear()

    def __contains__(self, exc_class: type[Exception]) -> bool:
        """Check if a handler is registered for an exception type."""
        return exc_class in self._handlers

    def __len__(self) -> int:
        """Return the number of registered handlers."""
        return len(self._handlers)

    @property
    def handlers(self) -> dict[type[Any], ExceptionHandler]:
        """Return a copy of the registered handlers."""
        return self._handlers.copy()


def default_exception_handler(request: Any, exc: Exception) -> dict[str, str]:
    """Default handler that returns a generic error dict.

    This is a fallback handler that can be used when no specific
    handler is registered.

    Args:
        request: The request object (unused).
        exc: The exception that was raised.

    Returns:
        A dict with error information.
    """
    return {"error": str(exc)}
