"""Tests for middleware functionality."""

import pytest

from tests.helpers import create_noop_receive, create_noop_send
from pykour import BaseMiddleware, Pykour, Request
from pykour.middleware import FunctionMiddleware
from pykour.response import Response


class TestBaseMiddleware:
    """Tests for BaseMiddleware class."""

    def test_base_middleware_is_abstract(self) -> None:
        """BaseMiddleware cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseMiddleware(None)

    def test_custom_middleware_implementation(self) -> None:
        """Custom middleware can be created by subclassing BaseMiddleware."""

        class CustomMiddleware(BaseMiddleware):
            async def __call__(self, scope, receive, send) -> None:
                await self.app(scope, receive, send)

        middleware = CustomMiddleware(lambda s, r, sn: None)
        assert middleware.app is not None


class TestFunctionMiddleware:
    """Tests for FunctionMiddleware class."""

    @pytest.mark.asyncio
    async def test_function_middleware_non_http_passthrough(self) -> None:
        """Non-HTTP requests are passed through without middleware processing."""
        called = False

        async def mock_app(scope, receive, send) -> None:
            nonlocal called
            called = True

        async def dispatch(request: Request, call_next) -> Response:
            return await call_next(request)

        middleware = FunctionMiddleware(mock_app, dispatch=dispatch)
        await middleware(
            {"type": "websocket"}, create_noop_receive(), create_noop_send()
        )

        assert called is True


class TestPykourMiddlewareIntegration:
    """Tests for middleware integration with Pykour application."""

    def test_add_middleware(self, tmp_path) -> None:
        """Middleware can be added to the application."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))

        class TestMiddleware(BaseMiddleware):
            async def __call__(self, scope, receive, send) -> None:
                await self.app(scope, receive, send)

        app.add_middleware(TestMiddleware)
        assert len(app._middleware_stack) == 1

    def test_middleware_decorator(self, tmp_path) -> None:
        """Middleware can be added using decorator."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))

        @app.middleware
        async def test_middleware(request: Request, call_next):
            return await call_next(request)

        assert len(app._middleware_stack) == 1
        assert app._middleware_stack[0][0] == FunctionMiddleware

    def test_multiple_middleware(self, tmp_path) -> None:
        """Multiple middleware can be added."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))

        class Middleware1(BaseMiddleware):
            async def __call__(self, scope, receive, send) -> None:
                await self.app(scope, receive, send)

        class Middleware2(BaseMiddleware):
            async def __call__(self, scope, receive, send) -> None:
                await self.app(scope, receive, send)

        app.add_middleware(Middleware1)
        app.add_middleware(Middleware2)

        assert len(app._middleware_stack) == 2

    @pytest.mark.asyncio
    async def test_middleware_execution_order(self, tmp_path) -> None:
        """Middleware is executed in the correct order."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        execution_order: list[str] = []

        @app.middleware
        async def first_middleware(request: Request, call_next):
            execution_order.append("first_before")
            response = await call_next(request)
            execution_order.append("first_after")
            return response

        @app.middleware
        async def second_middleware(request: Request, call_next):
            execution_order.append("second_before")
            response = await call_next(request)
            execution_order.append("second_after")
            return response

        # Simulate a request
        received_body = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            received_body.append(message)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }

        await app(scope, receive, send)

        # First added middleware should be outermost
        assert execution_order == [
            "first_before",
            "second_before",
            "second_after",
            "first_after",
        ]

    @pytest.mark.asyncio
    async def test_middleware_can_modify_response(self, tmp_path) -> None:
        """Middleware can modify the response."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))

        @app.middleware
        async def add_header_middleware(request: Request, call_next):
            response = await call_next(request)
            # Create a new response with added header
            return Response(
                content=response.body,
                status_code=response.status_code,
                headers={"X-Custom-Header": "test-value"},
            )

        received_messages: list[dict] = []

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            received_messages.append(message)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }

        await app(scope, receive, send)

        # Find the response.start message
        start_message = next(
            m for m in received_messages if m["type"] == "http.response.start"
        )
        headers_dict = {
            k.decode().lower(): v.decode() for k, v in start_message["headers"]
        }
        assert "x-custom-header" in headers_dict
        assert headers_dict["x-custom-header"] == "test-value"

    @pytest.mark.asyncio
    async def test_class_based_middleware_execution(self, tmp_path) -> None:
        """Class-based middleware is executed correctly."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        executed = False

        class TestMiddleware(BaseMiddleware):
            async def __call__(self, scope, receive, send) -> None:
                nonlocal executed
                executed = True
                await self.app(scope, receive, send)

        app.add_middleware(TestMiddleware)

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }

        await app(scope, receive, send)

        assert executed is True

    @pytest.mark.asyncio
    async def test_middleware_with_options(self, tmp_path) -> None:
        """Middleware can receive options."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))
        received_option = None

        class TestMiddleware(BaseMiddleware):
            def __init__(self, app, *, custom_option: str = "default"):
                super().__init__(app)
                self.custom_option = custom_option

            async def __call__(self, scope, receive, send) -> None:
                nonlocal received_option
                received_option = self.custom_option
                await self.app(scope, receive, send)

        app.add_middleware(TestMiddleware, custom_option="test_value")

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }

        await app(scope, receive, send)

        assert received_option == "test_value"

    @pytest.mark.asyncio
    async def test_middleware_stack_built_once(self, tmp_path) -> None:
        """Middleware stack is built only once."""
        routes_dir = tmp_path / "routes"
        routes_dir.mkdir()
        (routes_dir / "route.py").write_text(
            """
from pykour import JSONResponse

async def get():
    return JSONResponse({"message": "hello"})
"""
        )

        app = Pykour(routes_dir=str(routes_dir))

        @app.middleware
        async def test_middleware(request: Request, call_next):
            return await call_next(request)

        async def receive():
            return {"type": "http.request", "body": b""}

        async def send(message):
            pass

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }

        # First request builds the stack
        await app(scope, receive, send)
        first_app = app._app

        # Second request uses the same stack
        await app(scope, receive, send)
        second_app = app._app

        assert first_app is second_app


class TestMiddlewareImport:
    """Tests for middleware module imports."""

    def test_base_middleware_import(self) -> None:
        """BaseMiddleware can be imported from pykour."""
        from pykour import BaseMiddleware

        assert BaseMiddleware is not None

    def test_middleware_types_import(self) -> None:
        """Middleware types can be imported from pykour.middleware."""
        from pykour.middleware import (
            BaseMiddleware,
            CallNext,
            FunctionMiddleware,
            MiddlewareFunc,
        )

        assert BaseMiddleware is not None
        assert FunctionMiddleware is not None
        assert MiddlewareFunc is not None
        assert CallNext is not None
