"""Tests for pykour.core.middleware_builder module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from pykour.core.middleware_builder import (
    MiddlewareBuilder,
    create_middleware_decorator,
)
from pykour.middleware import BaseMiddleware


class MockMiddleware(BaseMiddleware):
    """Mock middleware for testing."""

    def __init__(self, app: Any, value: str = "default") -> None:
        super().__init__(app)
        self.value = value

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self.app(scope, receive, send)


class MockMiddleware2(BaseMiddleware):
    """Another mock middleware for testing."""

    def __init__(self, app: Any, number: int = 0) -> None:
        super().__init__(app)
        self.number = number

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        await self.app(scope, receive, send)


class TestMiddlewareBuilder:
    """Tests for MiddlewareBuilder class."""

    def test_initial_stack_empty(self) -> None:
        """Should have empty stack initially."""
        builder = MiddlewareBuilder()
        assert builder.stack == []

    def test_add_middleware(self) -> None:
        """Should add middleware to stack."""
        builder = MiddlewareBuilder()
        builder.add(MockMiddleware, value="test")

        assert len(builder.stack) == 1
        assert builder.stack[0] == (MockMiddleware, {"value": "test"})

    def test_add_multiple_middleware(self) -> None:
        """Should maintain order when adding multiple middleware."""
        builder = MiddlewareBuilder()
        builder.add(MockMiddleware, value="first")
        builder.add(MockMiddleware2, number=42)

        assert len(builder.stack) == 2
        assert builder.stack[0] == (MockMiddleware, {"value": "first"})
        assert builder.stack[1] == (MockMiddleware2, {"number": 42})


class TestAddFunctionMiddleware:
    """Tests for MiddlewareBuilder.add_function method."""

    @pytest.mark.asyncio
    async def test_add_function_middleware(self) -> None:
        """Should add function-based middleware."""
        from pykour.middleware import FunctionMiddleware

        builder = MiddlewareBuilder()

        async def my_middleware(request: Any, call_next: Any) -> Any:
            return await call_next(request)

        builder.add_function(my_middleware)

        assert len(builder.stack) == 1
        middleware_class, options = builder.stack[0]
        assert middleware_class is FunctionMiddleware
        assert options["dispatch"] is my_middleware


class TestBuild:
    """Tests for MiddlewareBuilder.build method."""

    def test_build_empty_stack(self) -> None:
        """Should return core app when stack is empty."""
        builder = MiddlewareBuilder()
        core_app = MagicMock(name="core_app")

        result = builder.build(core_app)

        assert result is core_app

    def test_build_single_middleware(self) -> None:
        """Should wrap core app with single middleware."""
        builder = MiddlewareBuilder()
        builder.add(MockMiddleware, value="wrapped")
        core_app = MagicMock(name="core_app")

        result = builder.build(core_app)

        assert isinstance(result, MockMiddleware)
        assert result.value == "wrapped"
        assert result.app is core_app

    def test_build_multiple_middleware_order(self) -> None:
        """Should apply middleware in correct order (first added is outermost)."""
        builder = MiddlewareBuilder()
        builder.add(MockMiddleware, value="outer")
        builder.add(MockMiddleware2, number=100)
        core_app = MagicMock(name="core_app")

        result = builder.build(core_app)

        # First middleware should be outermost
        assert isinstance(result, MockMiddleware)
        assert result.value == "outer"
        # Second middleware should wrap core app
        assert isinstance(result.app, MockMiddleware2)
        assert result.app.number == 100
        # Core app should be innermost
        assert result.app.app is core_app


class TestConfigureFromConfig:
    """Tests for MiddlewareBuilder.configure_from_config method."""

    def test_configure_none_config(self) -> None:
        """Should do nothing when config is None."""
        builder = MiddlewareBuilder(config=None)
        builder.configure_from_config()
        assert builder.stack == []

    def test_configure_trace_middleware(self) -> None:
        """Should configure trace middleware when enabled."""
        from pykour.middleware import TraceMiddleware

        config = create_mock_config(trace_enabled=True)
        builder = MiddlewareBuilder(config=config)

        builder.configure_from_config()

        assert len(builder.stack) == 1
        assert builder.stack[0][0] is TraceMiddleware

    def test_configure_multiple_middleware(self) -> None:
        """Should configure multiple middleware in correct order."""
        from pykour.middleware import LoggingMiddleware, TraceMiddleware

        config = create_mock_config(trace_enabled=True, logging_enabled=True)
        builder = MiddlewareBuilder(config=config)

        builder.configure_from_config()

        # Should have trace (outermost) then logging
        assert len(builder.stack) == 2
        assert builder.stack[0][0] is TraceMiddleware
        assert builder.stack[1][0] is LoggingMiddleware

    def test_configure_jwt_without_secret_raises_error(self) -> None:
        """Should raise ValueError when JWT enabled without secret."""
        config = create_mock_config(jwt_enabled=True, jwt_secret_key=None)
        builder = MiddlewareBuilder(config=config)

        with pytest.raises(ValueError, match="no secret_key configured"):
            builder.configure_from_config()


class TestCreateMiddlewareDecorator:
    """Tests for create_middleware_decorator function."""

    @pytest.mark.asyncio
    async def test_decorator_with_parentheses(self) -> None:
        """Should work when decorator is called with parentheses."""
        from pykour.middleware import FunctionMiddleware

        builder = MiddlewareBuilder()
        decorator = create_middleware_decorator(builder)

        @decorator()  # type: ignore[call-arg]
        async def my_middleware(request: Any, call_next: Any) -> Any:
            return await call_next(request)

        assert len(builder.stack) == 1
        assert builder.stack[0][0] is FunctionMiddleware

    @pytest.mark.asyncio
    async def test_decorator_without_parentheses(self) -> None:
        """Should work when decorator is called without parentheses."""
        from pykour.middleware import FunctionMiddleware

        builder = MiddlewareBuilder()
        decorator = create_middleware_decorator(builder)

        @decorator
        async def my_middleware(request: Any, call_next: Any) -> Any:
            return await call_next(request)

        assert len(builder.stack) == 1
        assert builder.stack[0][0] is FunctionMiddleware

    @pytest.mark.asyncio
    async def test_decorator_returns_original_function(self) -> None:
        """Should return the original function."""
        builder = MiddlewareBuilder()
        decorator = create_middleware_decorator(builder)

        async def my_middleware(request: Any, call_next: Any) -> Any:
            return await call_next(request)

        result = decorator(my_middleware)

        assert result is my_middleware


# Helper function to create mock config
def create_mock_config(
    *,
    trace_enabled: bool = False,
    logging_enabled: bool = False,
    security_enabled: bool = False,
    cors_enabled: bool = False,
    csrf_enabled: bool = False,
    rate_limit_enabled: bool = False,
    size_limit_enabled: bool = False,
    jwt_enabled: bool = False,
    jwt_secret_key: str | None = "test-secret",
) -> Any:
    """Create a mock middleware config for testing."""
    config = MagicMock()

    # Trace config
    config.trace.enabled = trace_enabled

    # Logging config
    config.logging.enabled = logging_enabled
    config.logging.logger_name = "pykour"
    config.logging.level = "INFO"
    config.logging.exclude_paths = []
    config.logging.log_request_headers = False
    config.logging.log_response_headers = False

    # Security config
    config.security.enabled = security_enabled
    config.security.csp = None
    config.security.hsts_max_age = 31536000
    config.security.hsts_include_subdomains = True
    config.security.hsts_preload = False
    config.security.x_content_type_options = "nosniff"
    config.security.x_frame_options = "DENY"
    config.security.x_xss_protection = "1; mode=block"
    config.security.referrer_policy = "strict-origin-when-cross-origin"
    config.security.csp_report_only = False
    config.security.exclude_paths = []

    # CORS config
    config.cors.enabled = cors_enabled
    config.cors.allow_origins = ["*"]
    config.cors.allow_methods = ["*"]
    config.cors.allow_headers = ["*"]
    config.cors.allow_credentials = False
    config.cors.expose_headers = []
    config.cors.max_age = 600

    # CSRF config
    config.csrf.enabled = csrf_enabled
    config.csrf.cookie_name = "csrf_token"
    config.csrf.header_name = "X-CSRF-Token"
    config.csrf.cookie_path = "/"
    config.csrf.cookie_domain = None
    config.csrf.cookie_secure = True
    config.csrf.cookie_httponly = False
    config.csrf.cookie_samesite = "lax"
    config.csrf.cookie_max_age = 3600
    config.csrf.exclude_paths = []

    # Rate limit config
    config.rate_limit.enabled = rate_limit_enabled
    config.rate_limit.requests_per_second = 10
    config.rate_limit.burst_size = 20
    config.rate_limit.exclude_paths = []
    config.rate_limit.include_headers = True
    config.rate_limit.path_configs = {}

    # Size limit config
    config.size_limit.enabled = size_limit_enabled
    config.size_limit.max_size = 1048576
    config.size_limit.max_size_by_content_type = None
    config.size_limit.exclude_paths = []
    config.size_limit.check_content_length = True
    config.size_limit.check_body_size = True

    # JWT config
    config.jwt.enabled = jwt_enabled
    config.jwt.secret_key = jwt_secret_key
    config.jwt.secret_keys = None
    config.jwt.algorithm = "HS256"
    config.jwt.exclude_paths = []
    config.jwt.auto_error = True

    return config
