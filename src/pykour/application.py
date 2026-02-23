"""Pykour ASGI Application."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, cast

from pykour.config import PykourConfig, load_config
from pykour.core.config_resolver import (
    _USE_CONFIG_DEFAULT,
    resolve_cache,
    resolve_database,
    resolve_debug,
    resolve_health_config,
    resolve_metrics_config,
    resolve_openapi_config,
    resolve_routes_dir,
)
from pykour.core.exceptions import handle_exception as _handle_exception_impl
from pykour.core.lifespan import LifespanManager
from pykour.core.middleware_builder import MiddlewareBuilder
from pykour.core.request_handler import RequestHandler
from pykour.core.websocket import handle_websocket
from pykour.di import ServiceContainer
from pykour.exception_handlers import ExceptionHandler, ExceptionHandlerRegistry
from pykour.exceptions import HTTPException
from pykour.health.handler import HealthCheckHandler, setup_health_check
from pykour.injection import ParameterInjector
from pykour.metrics.collector import MetricsCollector
from pykour.metrics.handler import MetricsHandler, setup_metrics
from pykour.middleware import BaseMiddleware, MiddlewareFunc
from pykour.openapi.routes import OpenAPIRouteHandler, setup_openapi
from pykour.request import Request
from pykour.response import Response
from pykour.router import Router
from pykour.schema import ValidationError
from pykour.types import Receive, Scope, Send

from pykour.core.exceptions import (
    handle_http_exception,
    handle_validation_exception,
)

if TYPE_CHECKING:
    from pykour.cache.storage import CacheStorage
    from pykour.db import Database


class Pykour:
    """Pykour ASGI Application with file-based routing.

    A lightweight ASGI web framework using Next.js-style file-based routing.

    Example:
        ```python
        from pykour import Pykour

        app = Pykour(routes_dir="routes")
        ```

        routes/api/users/route.py:
        ```python
        from pykour import Request, JSONResponse, Query

        async def get(
            request: Request,
            page: int = Query(default=1, ge=1),
        ) -> JSONResponse:
            return JSONResponse({"users": [], "page": page})

        async def post(request: Request) -> JSONResponse:
            return JSONResponse({"created": True})
        ```

        routes/api/users/[id]/route.py:
        ```python
        from pykour import Request, JSONResponse, Path

        async def get(request: Request, id: int = Path()) -> JSONResponse:
            return JSONResponse({"id": id})
        ```

    With database:
        ```python
        from pykour import Pykour
        from pykour.db import Database

        db = Database("sqlite:///app.db")
        app = Pykour(routes_dir="routes", database=db)
        ```

        routes/api/users/route.py:
        ```python
        from pykour import Request, JSONResponse
        from pykour.db import Database
        from pykour.di import Depends

        async def get(request: Request, db: Database = Depends()) -> JSONResponse:
            users = await db.select("*").from_("users").fetch_all()
            return JSONResponse({"users": users})
        ```
    """

    def __init__(
        self,
        routes_dir: str | Path | None = None,
        database: "Database | None" = None,
        cache: "CacheStorage | None" = None,
        debug: bool | None = None,
        *,
        config_file: str | Path | None = None,
        auto_load_config: bool = True,
        title: str | None = None,
        version: str | None = None,
        description: str | None = None,
        docs_url: str | None | object = _USE_CONFIG_DEFAULT,
        openapi_url: str | None | object = _USE_CONFIG_DEFAULT,
        redoc_url: str | None | object = _USE_CONFIG_DEFAULT,
        health_url: str | None | object = _USE_CONFIG_DEFAULT,
        metrics_url: str | None | object = _USE_CONFIG_DEFAULT,
    ) -> None:
        """Initialize Pykour application.

        Args:
            routes_dir: Directory containing route.py files. If not specified,
                uses config file value or defaults to a "routes" subdirectory
                in the same directory as the file that calls Pykour().
            database: Optional database instance for dependency injection.
                If not specified and config file has database.url, creates one.
            cache: Optional cache storage for response and data caching.
                If not specified and config file has cache.url, creates one.
            debug: Enable debug mode for detailed error tracebacks.
                If None, reads from config file or PYKOUR_DEBUG environment variable.
            config_file: Path to configuration file (pykour.toml).
                If not specified, auto-discovers pykour.toml in current directory.
            auto_load_config: Whether to auto-discover pykour.toml. Default True.
            title: API title for OpenAPI documentation.
            version: API version for OpenAPI documentation.
            description: API description for OpenAPI documentation.
            docs_url: URL path for Swagger UI. Set to None to disable.
            openapi_url: URL path for OpenAPI JSON schema. Set to None to disable.
            redoc_url: URL path for ReDoc. Set to None to disable.
            health_url: URL path for health check endpoint. Set to None to disable.
            metrics_url: URL path for Prometheus metrics endpoint. Set to None to disable.
        """
        # Load configuration (priority: code > env > config file > defaults)
        self._pykour_config = load_config(
            config_file=config_file,
            auto_discover=auto_load_config,
        )
        cfg = self._pykour_config

        # Resolve configuration using helper functions
        resolved_routes_dir = resolve_routes_dir(routes_dir, cfg, caller_stack_level=3)
        self._debug = resolve_debug(debug, cfg)
        self._database = resolve_database(database, cfg)
        self._cache = resolve_cache(cache, cfg)

        # Initialize core components
        self._router = Router(resolved_routes_dir)
        self._services = ServiceContainer()

        # Auto-register database in service container for DI
        if self._database is not None:
            from pykour.db.database import Database as DatabaseClass

            self._services.register_instance(DatabaseClass, self._database)

        # Auto-register cache client in service container for DI
        if self._cache is not None:
            from pykour.cache.client import Cache

            cache_client = Cache(self._cache)
            self._services.register_instance(Cache, cache_client)

        # Initialize exception handler registry with default handlers
        self._exception_handlers = ExceptionHandlerRegistry()
        self._exception_handlers.add(HTTPException, handle_http_exception)
        self._exception_handlers.add(ValidationError, handle_validation_exception)

        # Initialize parameter injector
        self._injector = ParameterInjector(self._services, self._database)

        # Initialize request handler
        self._request_handler = RequestHandler(
            self._router, self._injector, self._cache
        )

        # Initialize middleware builder
        self._middleware_builder = MiddlewareBuilder(cfg.middleware)
        self._middleware_builder.configure_from_config()

        # Initialize lifespan manager
        # Use lambda to allow method to be patched in tests
        self._lifespan = LifespanManager(
            self._database,
            self._cache,
            lambda: self._build_middleware_stack(),
        )

        # Resolve and setup OpenAPI
        self._openapi_config = resolve_openapi_config(
            cfg, title, version, description, docs_url, openapi_url, redoc_url
        )
        self._openapi_handler: OpenAPIRouteHandler | None = None
        if (
            self._openapi_config.docs_url
            or self._openapi_config.openapi_url
            or self._openapi_config.redoc_url
        ):
            self._openapi_handler = setup_openapi(self, self._openapi_config)

        # Resolve and setup health check
        self._health_config = resolve_health_config(cfg, health_url)
        self._health_handler: HealthCheckHandler | None = None
        if self._health_config.health_url is not None:
            self._health_handler = setup_health_check(self._health_config)

        # Resolve and setup metrics
        self._metrics_config = resolve_metrics_config(
            cfg, self._health_config.health_url, metrics_url
        )
        self._metrics_collector: MetricsCollector | None = None
        self._metrics_handler: MetricsHandler | None = None
        if self._metrics_config.metrics_url is not None:
            self._metrics_collector = MetricsCollector(
                buckets=self._metrics_config.latency_buckets
            )
            self._metrics_handler = setup_metrics(
                self._metrics_config, self._metrics_collector
            )

    @property
    def config(self) -> PykourConfig:
        """Get the loaded configuration.

        Returns:
            PykourConfig instance with merged configuration values.
        """
        return self._pykour_config

    @property
    def services(self) -> ServiceContainer:
        """Get the service container for dependency injection.

        Example:
            app.services.register(UserService, UserServiceImpl)
            app.services.register(ConfigService, scope=Scope.SINGLETON)
        """
        return self._services

    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled.

        Debug mode shows detailed error tracebacks in responses.
        """
        return self._debug

    @property
    def openapi_schema(self) -> dict[str, Any]:
        """Get the OpenAPI schema for this application.

        The schema is generated from route handlers and cached.

        Returns:
            OpenAPI document dictionary.

        Raises:
            RuntimeError: If OpenAPI documentation is disabled.
        """
        if self._openapi_handler is None:
            raise RuntimeError(
                "OpenAPI documentation is disabled. "
                "Enable it by setting docs_url or openapi_url."
            )
        return self._openapi_handler.get_openapi_schema()

    @property
    def exception_handlers(self) -> ExceptionHandlerRegistry:
        """Get the exception handler registry.

        Example:
            # Check if handler is registered
            if HTTPException in app.exception_handlers:
                ...
        """
        return self._exception_handlers

    def add_exception_handler(
        self,
        exc_class: type[Exception],
        handler: ExceptionHandler,
    ) -> None:
        """Register a custom exception handler.

        Handlers are matched using the exception's MRO, so a handler for
        a parent class will catch subclass exceptions unless a more
        specific handler is registered.

        Args:
            exc_class: The exception class to handle.
            handler: A callable that accepts (Request, Exception) and
                returns a Response. Can be async or sync.

        Example:
            async def handle_value_error(request, exc):
                return JSONResponse(
                    {"error": str(exc)},
                    status_code=400,
                )

            app.add_exception_handler(ValueError, handle_value_error)
        """
        self._exception_handlers.add(exc_class, handler)

    def exception_handler(
        self,
        exc_class: type[Exception],
    ) -> Callable[[ExceptionHandler], ExceptionHandler]:
        """Decorator to register an exception handler.

        Args:
            exc_class: The exception class to handle.

        Returns:
            Decorator function.

        Example:
            @app.exception_handler(NotFoundException)
            async def handle_not_found(request, exc):
                return JSONResponse(
                    {"error": exc.detail, "path": request.path},
                    status_code=404,
                )

            # Custom exception with handler
            class ItemNotFoundError(NotFoundException):
                def __init__(self, item_id: int):
                    self.item_id = item_id
                    super().__init__(f"Item {item_id} not found")

            @app.exception_handler(ItemNotFoundError)
            async def handle_item_not_found(request, exc):
                return JSONResponse(
                    {"error": exc.detail, "item_id": exc.item_id},
                    status_code=404,
                )
        """

        def decorator(func: ExceptionHandler) -> ExceptionHandler:
            self.add_exception_handler(exc_class, func)
            return func

        return decorator

    def enable_metrics(self) -> None:
        """Enable metrics collection middleware.

        This adds the MetricsMiddleware to collect request metrics
        (latency, request count, etc.) that are exposed via the /metrics endpoint.

        Must be called before the application starts processing requests.

        Raises:
            RuntimeError: If metrics endpoint is disabled (metrics_url=None).

        Example:
            app = Pykour(routes_dir="routes", metrics_url="/metrics")
            app.enable_metrics()  # Start collecting metrics
        """
        if self._metrics_collector is None:
            raise RuntimeError(
                "Metrics endpoint is disabled. "
                "Enable it by setting metrics_url in the Pykour constructor."
            )

        from pykour.metrics.middleware import MetricsMiddleware

        self.add_middleware(
            MetricsMiddleware,
            collector=self._metrics_collector,
            config=self._metrics_config,
        )

    def add_middleware(
        self,
        middleware_class: type[BaseMiddleware],
        **options: Any,
    ) -> None:
        """Add middleware to the application.

        Middleware is executed in the order it is added, with the first
        middleware being the outermost wrapper.

        Args:
            middleware_class: The middleware class to add.
            **options: Options to pass to the middleware constructor.

        Example:
            class LoggingMiddleware(BaseMiddleware):
                async def __call__(self, scope, receive, send):
                    print(f"Request: {scope['path']}")
                    await self.app(scope, receive, send)

            app.add_middleware(LoggingMiddleware)
        """
        self._middleware_builder.add(middleware_class, **options)

    def middleware(
        self,
        func: MiddlewareFunc | None = None,
    ) -> Callable[[MiddlewareFunc], MiddlewareFunc] | MiddlewareFunc:
        """Decorator to add function-based middleware.

        Can be used with or without parentheses.

        Example:
            @app.middleware
            async def logging_middleware(request, call_next):
                print(f"Request: {request.method} {request.path}")
                response = await call_next(request)
                print(f"Response: {response.status_code}")
                return response
        """

        def decorator(fn: MiddlewareFunc) -> MiddlewareFunc:
            self._middleware_builder.add_function(fn)
            return fn

        if func is not None:
            return decorator(func)
        return decorator

    def register_route(
        self,
        path: str,
        handlers: dict[str, Any],
    ) -> None:
        """Register a route programmatically.

        This allows adding routes without creating route.py files.

        Args:
            path: URL path pattern (e.g., "/api/users", "/api/users/[id]").
            handlers: Dict mapping HTTP methods to handler functions.
                Keys should be uppercase (e.g., "GET", "POST").

        Example:
            async def list_users(request):
                return JSONResponse({"users": []})

            app.register_route("/api/users", {"GET": list_users})
        """
        self._router.register_route(path, handlers)

    def register_crud(
        self,
        path: str,
        table: type,
        *,
        operations: list[str] | None = None,
        list_config: Any | None = None,
        id_field: str | None = None,
        exclude_fields: list[str] | None = None,
        readonly_fields: list[str] | None = None,
    ) -> None:
        """Register CRUD endpoints for a Table.

        Automatically creates list, get, create, update, and delete
        endpoints for the specified Table.

        Args:
            path: Base path for the endpoints (e.g., "/api/users").
            table: Table class to generate CRUD for.
            operations: List of operations to enable.
                Options: "list", "get", "create", "update", "delete".
                Defaults to all operations.
            list_config: Configuration for list endpoint (ListConfig instance).
            id_field: Primary key field name. Auto-detected if not provided.
            exclude_fields: Fields to exclude from the API.
            readonly_fields: Fields that cannot be set on create/update.

        Example:
            from pykour.db.migrations import Table, Column, Integer, String

            class UserTable(Table):
                __tablename__ = "users"
                id = Column(Integer(), primary_key=True, autoincrement=True)
                name = Column(String(100), nullable=False)

            app.register_crud("/api/users", UserTable)
        """
        from pykour.crud.registrar import CRUDRegistrar
        from pykour.db.migrations import Table as TableClass

        registrar = CRUDRegistrar(self)
        registrar.register(
            path=path,
            table=cast(type[TableClass], table),
            operations=operations,
            list_config=list_config,
            id_field=id_field,
            exclude_fields=exclude_fields,
            readonly_fields=readonly_fields,
        )

    def _build_middleware_stack(self) -> Any:
        """Build the middleware stack wrapping the core app.

        Returns:
            The wrapped ASGI application.
        """
        return self._middleware_builder.build(self._core_asgi_app)

    async def _core_asgi_app(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Core ASGI application handler (without middleware)."""
        # Check health check endpoint first (lightweight)
        if self._health_handler is not None:
            if await self._health_handler.handle(scope, receive, send):
                return

        # Check metrics endpoint
        if self._metrics_handler is not None:
            if await self._metrics_handler.handle(scope, receive, send):
                return

        # Check OpenAPI routes
        if self._openapi_handler is not None:
            if await self._openapi_handler.handle(scope, receive, send):
                return

        # Handle request
        try:
            response = await self._request_handler.handle(scope, receive)
        except Exception as e:
            request = Request(scope, receive, {})
            response = await self._handle_exception(request, e)

        await response(scope, receive, send)

    async def _handle_exception(self, request: Request, exc: Exception) -> Response:
        """Handle exceptions during request processing.

        Delegates to the core exception handling implementation.

        Args:
            request: The request object.
            exc: The exception that was raised.

        Returns:
            Response from the exception handler.
        """
        return await _handle_exception_impl(
            request, exc, self._exception_handlers, self._debug
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI application entry point."""
        if scope["type"] == "lifespan":
            await self._lifespan.handle_lifespan(scope, receive, send)
            return

        # Auto-start if not started (for testing without lifespan)
        await self._lifespan.startup()

        if scope["type"] == "http":
            app = self._lifespan.app
            if app is not None:
                await app(scope, receive, send)
        elif scope["type"] == "websocket":
            await self._handle_websocket(scope, receive, send)

    async def _handle_websocket(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle WebSocket connections.

        Delegates to the core websocket handling implementation.

        Args:
            scope: ASGI WebSocket scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        await handle_websocket(scope, receive, send, self._router, self._injector)
