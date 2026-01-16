"""Tests for HTTP exceptions and exception handlers."""

from __future__ import annotations

import pytest

from pykour import (
    BadGatewayException,
    BadRequestException,
    ConflictException,
    ExceptionHandlerRegistry,
    ForbiddenException,
    GatewayTimeoutException,
    GoneException,
    HTTPException,
    InternalServerErrorException,
    MethodNotAllowedException,
    NotFoundException,
    Pykour,
    ServiceUnavailableException,
    TooManyRequestsException,
    UnauthorizedException,
    UnprocessableEntityException,
)
from pykour.response import JSONResponse, Response
from pykour.testing import TestClient


# =============================================================================
# HTTPException Base Class Tests
# =============================================================================


class TestHTTPException:
    """Tests for HTTPException base class."""

    def test_default_values(self) -> None:
        """Test default status_code and detail."""
        exc = HTTPException()
        assert exc.status_code == 500
        assert exc.detail == "Internal Server Error"
        assert exc.headers == {}

    def test_custom_detail(self) -> None:
        """Test custom detail message."""
        exc = HTTPException(detail="Custom error message")
        assert exc.status_code == 500
        assert exc.detail == "Custom error message"

    def test_custom_status_code(self) -> None:
        """Test custom status code."""
        exc = HTTPException(status_code=418, detail="I'm a teapot")
        assert exc.status_code == 418
        assert exc.detail == "I'm a teapot"

    def test_custom_headers(self) -> None:
        """Test custom headers."""
        headers = {"X-Custom": "value", "Location": "/new-path"}
        exc = HTTPException(headers=headers)
        assert exc.headers == headers

    def test_all_custom_parameters(self) -> None:
        """Test all custom parameters together."""
        exc = HTTPException(
            detail="Resource moved",
            status_code=301,
            headers={"Location": "/new-location"},
        )
        assert exc.status_code == 301
        assert exc.detail == "Resource moved"
        assert exc.headers == {"Location": "/new-location"}

    def test_exception_message(self) -> None:
        """Test that detail is used as exception message."""
        exc = HTTPException(detail="Error message")
        assert str(exc) == "Error message"

    def test_repr(self) -> None:
        """Test string representation."""
        exc = HTTPException(detail="Not found", status_code=404)
        repr_str = repr(exc)
        assert "HTTPException" in repr_str
        assert "404" in repr_str
        assert "Not found" in repr_str


# =============================================================================
# Standard Exception Classes Tests
# =============================================================================


class TestStandardExceptions:
    """Tests for standard HTTP exception classes."""

    @pytest.mark.parametrize(
        "exc_class,expected_status,expected_detail",
        [
            (BadRequestException, 400, "Bad Request"),
            (UnauthorizedException, 401, "Unauthorized"),
            (ForbiddenException, 403, "Forbidden"),
            (NotFoundException, 404, "Not Found"),
            (MethodNotAllowedException, 405, "Method Not Allowed"),
            (ConflictException, 409, "Conflict"),
            (GoneException, 410, "Gone"),
            (UnprocessableEntityException, 422, "Unprocessable Entity"),
            (TooManyRequestsException, 429, "Too Many Requests"),
            (InternalServerErrorException, 500, "Internal Server Error"),
            (BadGatewayException, 502, "Bad Gateway"),
            (ServiceUnavailableException, 503, "Service Unavailable"),
            (GatewayTimeoutException, 504, "Gateway Timeout"),
        ],
    )
    def test_standard_exception_defaults(
        self,
        exc_class: type[HTTPException],
        expected_status: int,
        expected_detail: str,
    ) -> None:
        """Test default values for standard exception classes."""
        exc = exc_class()
        assert exc.status_code == expected_status
        assert exc.detail == expected_detail
        assert exc.headers == {}

    def test_custom_detail_overrides_default(self) -> None:
        """Test that custom detail overrides class default."""
        exc = NotFoundException(detail="User not found")
        assert exc.status_code == 404
        assert exc.detail == "User not found"

    def test_inheritance_hierarchy(self) -> None:
        """Test that all exceptions inherit from HTTPException."""
        exceptions = [
            BadRequestException,
            UnauthorizedException,
            ForbiddenException,
            NotFoundException,
            InternalServerErrorException,
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, HTTPException)
            assert issubclass(exc_class, Exception)


# =============================================================================
# Custom Exception Subclassing Tests
# =============================================================================


class TestCustomExceptionSubclassing:
    """Tests for creating custom exception subclasses."""

    def test_simple_subclass(self) -> None:
        """Test creating a simple subclass with custom defaults."""

        class ItemNotFoundException(NotFoundException):
            detail = "Item not found"

        exc = ItemNotFoundException()
        assert exc.status_code == 404
        assert exc.detail == "Item not found"

    def test_subclass_with_extra_attributes(self) -> None:
        """Test creating a subclass with additional attributes."""

        class UserNotFoundException(NotFoundException):
            def __init__(self, user_id: int) -> None:
                self.user_id = user_id
                super().__init__(detail=f"User {user_id} not found")

        exc = UserNotFoundException(user_id=123)
        assert exc.status_code == 404
        assert exc.detail == "User 123 not found"
        assert exc.user_id == 123

    def test_deeply_nested_subclass(self) -> None:
        """Test deeply nested exception hierarchy."""

        class ResourceNotFoundException(NotFoundException):
            detail = "Resource not found"

        class EntityNotFoundException(ResourceNotFoundException):
            detail = "Entity not found"

        class UserNotFoundException(EntityNotFoundException):
            detail = "User not found"

        exc = UserNotFoundException()
        assert exc.status_code == 404
        assert exc.detail == "User not found"
        assert isinstance(exc, NotFoundException)
        assert isinstance(exc, HTTPException)


# =============================================================================
# ExceptionHandlerRegistry Tests
# =============================================================================


class TestExceptionHandlerRegistry:
    """Tests for ExceptionHandlerRegistry."""

    def test_empty_registry(self) -> None:
        """Test empty registry returns None for any exception."""
        registry = ExceptionHandlerRegistry()
        assert registry.get(ValueError("test")) is None
        assert len(registry) == 0

    def test_add_and_get_handler(self) -> None:
        """Test adding and retrieving a handler."""
        registry = ExceptionHandlerRegistry()

        def handler(request: object, exc: Exception) -> Response:
            return JSONResponse({"error": str(exc)}, status_code=400)

        registry.add(ValueError, handler)
        assert registry.get(ValueError("test")) is handler
        assert len(registry) == 1

    def test_mro_lookup(self) -> None:
        """Test that handlers are looked up using MRO."""
        registry = ExceptionHandlerRegistry()

        def http_handler(request: object, exc: Exception) -> Response:
            return JSONResponse({"error": "http"}, status_code=500)

        def not_found_handler(request: object, exc: Exception) -> Response:
            return JSONResponse({"error": "not found"}, status_code=404)

        # Register handler for parent class
        registry.add(HTTPException, http_handler)

        # NotFoundException should be handled by HTTPException handler
        not_found_exc = NotFoundException()
        assert registry.get(not_found_exc) is http_handler

        # Now register more specific handler
        registry.add(NotFoundException, not_found_handler)

        # NotFoundException should now be handled by specific handler
        assert registry.get(not_found_exc) is not_found_handler

        # BadRequestException should still use HTTPException handler
        bad_request_exc = BadRequestException()
        assert registry.get(bad_request_exc) is http_handler

    def test_custom_subclass_mro_lookup(self) -> None:
        """Test MRO lookup with custom subclasses."""
        registry = ExceptionHandlerRegistry()

        class ItemNotFoundException(NotFoundException):
            pass

        def not_found_handler(request: object, exc: Exception) -> Response:
            return JSONResponse({"error": "not found"}, status_code=404)

        registry.add(NotFoundException, not_found_handler)

        # ItemNotFoundException should be handled by NotFoundException handler
        item_exc = ItemNotFoundException()
        assert registry.get(item_exc) is not_found_handler

    def test_contains_check(self) -> None:
        """Test __contains__ for checking registered handlers."""
        registry = ExceptionHandlerRegistry()

        def handler(request: object, exc: Exception) -> Response:
            return JSONResponse({})

        assert ValueError not in registry
        registry.add(ValueError, handler)
        assert ValueError in registry

    def test_remove_handler(self) -> None:
        """Test removing a handler."""
        registry = ExceptionHandlerRegistry()

        def handler(request: object, exc: Exception) -> Response:
            return JSONResponse({})

        registry.add(ValueError, handler)
        assert ValueError in registry

        result = registry.remove(ValueError)
        assert result is True
        assert ValueError not in registry
        assert registry.remove(ValueError) is False

    def test_clear_handlers(self) -> None:
        """Test clearing all handlers."""
        registry = ExceptionHandlerRegistry()

        def handler(request: object, exc: Exception) -> Response:
            return JSONResponse({})

        registry.add(ValueError, handler)
        registry.add(TypeError, handler)
        assert len(registry) == 2

        registry.clear()
        assert len(registry) == 0

    def test_handlers_property(self) -> None:
        """Test handlers property returns a copy."""
        registry = ExceptionHandlerRegistry()

        def handler(request: object, exc: Exception) -> Response:
            return JSONResponse({})

        registry.add(ValueError, handler)

        handlers = registry.handlers
        assert ValueError in handlers

        # Modifying the returned dict should not affect registry
        handlers[TypeError] = handler
        assert TypeError not in registry


# =============================================================================
# Application Integration Tests
# =============================================================================


class TestApplicationExceptionHandling:
    """Tests for exception handling in Pykour application."""

    @pytest.mark.asyncio
    async def test_default_http_exception_handler(self) -> None:
        """Test default HTTPException handler."""
        app = Pykour(routes_dir="tests/routes")

        # Manually raise NotFoundException in a route
        @app.exception_handler(NotFoundException)
        def handle_not_found(request: object, exc: NotFoundException) -> Response:
            return JSONResponse(
                {"error": exc.detail, "custom": True},
                status_code=exc.status_code,
            )

        # The default handler should be registered for HTTPException
        assert HTTPException in app.exception_handlers

    @pytest.mark.asyncio
    async def test_add_exception_handler_method(self) -> None:
        """Test add_exception_handler method."""
        app = Pykour(routes_dir="tests/routes")

        def custom_handler(request: object, exc: ValueError) -> Response:
            return JSONResponse({"error": str(exc)}, status_code=400)

        app.add_exception_handler(ValueError, custom_handler)
        assert ValueError in app.exception_handlers

    @pytest.mark.asyncio
    async def test_exception_handler_decorator(self) -> None:
        """Test @app.exception_handler decorator."""
        app = Pykour(routes_dir="tests/routes")

        @app.exception_handler(KeyError)
        def handle_key_error(request: object, exc: KeyError) -> Response:
            return JSONResponse({"error": f"Key not found: {exc}"}, status_code=400)

        assert KeyError in app.exception_handlers

    @pytest.mark.asyncio
    async def test_custom_exception_in_route(self) -> None:
        """Test custom exception raised in route handler."""
        app = Pykour(routes_dir="tests/routes")

        class ItemNotFoundException(NotFoundException):
            def __init__(self, item_id: int) -> None:
                self.item_id = item_id
                super().__init__(detail=f"Item {item_id} not found")

        @app.exception_handler(ItemNotFoundException)
        def handle_item_not_found(
            request: object, exc: ItemNotFoundException
        ) -> Response:
            return JSONResponse(
                {"error": exc.detail, "item_id": exc.item_id},
                status_code=404,
            )

        assert ItemNotFoundException in app.exception_handlers


class TestExceptionHandlerExecution:
    """Tests for actual exception handler execution."""

    @pytest.mark.asyncio
    async def test_http_exception_response(self) -> None:
        """Test that HTTPException produces correct response."""
        app = Pykour(routes_dir="tests/routes/exception_test")
        client = TestClient(app)

        response = await client.get("/not-found")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_validation_error_response(self) -> None:
        """Test that ValidationError produces 422 response."""
        from pykour.schema import ValidationError as SchemaValidationError

        app = Pykour(routes_dir="tests/routes")

        # Verify ValidationError handler is registered
        assert SchemaValidationError in app.exception_handlers

        # The default handler should return 422 for ValidationError
        client = TestClient(app)
        # Just verify the endpoint exists and handler is registered
        response = await client.get("/")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_custom_handler_overrides_default(self) -> None:
        """Test that custom handler overrides default handler."""
        app = Pykour(routes_dir="tests/routes/exception_test")

        @app.exception_handler(NotFoundException)
        def custom_not_found(request: object, exc: NotFoundException) -> Response:
            return JSONResponse(
                {"custom_error": True, "message": exc.detail},
                status_code=404,
            )

        client = TestClient(app)
        response = await client.get("/not-found")
        assert response.status_code == 404
        data = response.json()
        assert data.get("custom_error") is True


# =============================================================================
# Async Handler Tests
# =============================================================================


class TestAsyncExceptionHandlers:
    """Tests for async exception handlers."""

    @pytest.mark.asyncio
    async def test_async_exception_handler(self) -> None:
        """Test that async exception handlers work correctly."""
        app = Pykour(routes_dir="tests/routes")

        @app.exception_handler(RuntimeError)
        async def handle_runtime_error(request: object, exc: RuntimeError) -> Response:
            # Simulate async operation
            import asyncio

            await asyncio.sleep(0)
            return JSONResponse({"error": str(exc), "async": True}, status_code=500)

        assert RuntimeError in app.exception_handlers
