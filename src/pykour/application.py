"""Pykour ASGI Application."""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, cast

from pykour.config import PykourConfig, load_config
from pykour.core.exceptions import (
    handle_exception as _handle_exception_impl,
    handle_http_exception,
    handle_validation_exception,
)
from pykour.core.handler import (
    deserialize_response,
    interpolate_cache_key,
    interpolate_header_value,
    serialize_response,
)
from pykour.core.websocket import handle_websocket
from pykour.di import ServiceContainer
from pykour.exception_handlers import ExceptionHandler, ExceptionHandlerRegistry
from pykour.exceptions import HTTPException
from pykour.health.config import HealthCheckConfig
from pykour.health.handler import HealthCheckHandler, setup_health_check
from pykour.metrics.collector import MetricsCollector
from pykour.metrics.config import MetricsConfig
from pykour.metrics.handler import MetricsHandler, setup_metrics
from pykour.injection import ParameterInjector
from pykour.middleware import BaseMiddleware, FunctionMiddleware, MiddlewareFunc
from pykour.openapi.config import OpenAPIConfig
from pykour.openapi.routes import OpenAPIRouteHandler, setup_openapi
from pykour.request import Request
from pykour.response import JSONResponse, Response
from pykour.router import Router
from pykour.schema import ValidationError
from pykour.types import Receive, Scope, Send

if TYPE_CHECKING:
    from pykour.cache.storage import CacheStorage
    from pykour.db import Database


# Sentinel value to indicate that routes_dir should be resolved from the caller's directory
_CALLER_ROUTES_DIR: object = object()

# Sentinel value to indicate "use config file default"
_USE_CONFIG_DEFAULT: object = object()


def _resolve_routes_dir(routes_dir: str | Path | object) -> Path:
    """Resolve routes_dir to an absolute Path.

    If routes_dir is the sentinel value _CALLER_ROUTES_DIR, resolves to a "routes"
    subdirectory in the same directory as the file that called Pykour().

    Args:
        routes_dir: Explicitly specified routes directory, or sentinel value.

    Returns:
        Resolved Path to the routes directory.
    """
    if routes_dir is not _CALLER_ROUTES_DIR:
        return Path(routes_dir)  # type: ignore[arg-type]

    # Resolve from caller's directory
    # stack[0] = _resolve_routes_dir
    # stack[1] = __init__
    # stack[2] = Pykour() caller
    stack = inspect.stack()

    if len(stack) < 3:
        # Stack too shallow (unlikely but handle defensively)
        return Path.cwd() / "routes"

    caller_frame = stack[2]
    caller_file = caller_frame.filename

    # Handle REPL, exec(), or other non-file contexts
    if not caller_file or caller_file.startswith("<"):
        return Path.cwd() / "routes"

    caller_path = Path(caller_file)

    # Handle frozen executables or missing files
    if not caller_path.exists():
        return Path.cwd() / "routes"

    return caller_path.parent.resolve() / "routes"


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
        from pykour.db import Database, Depends

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

        # Resolve routes_dir (code > config file > caller's directory)
        if routes_dir is not None:
            resolved_routes_dir = _resolve_routes_dir(routes_dir)
        elif cfg.app.routes_dir != "routes":
            # Config file specified a non-default value
            resolved_routes_dir = Path(cfg.app.routes_dir)
        else:
            # Use caller's directory as default
            resolved_routes_dir = _resolve_routes_dir(_CALLER_ROUTES_DIR)

        self._router = Router(resolved_routes_dir)
        self._started = False
        self._startup_lock = asyncio.Lock()
        self._middleware_stack: list[tuple[type[BaseMiddleware], dict[str, Any]]] = []
        self._app: Any = None
        self._services = ServiceContainer()

        # Determine debug mode (code > env/config)
        if debug is not None:
            self._debug = debug
        else:
            self._debug = cfg.app.debug

        # Database: explicit > config file
        if database is not None:
            self._database = database
        elif cfg.database.url:
            from pykour.db.database import Database as DatabaseClass

            self._database = DatabaseClass(
                url=cfg.database.url,
                min_size=cfg.database.min_size,
                max_size=cfg.database.max_size,
                enable_access_policies=cfg.database.enable_access_policies,
            )
        else:
            self._database = None

        # Cache: explicit > config file
        if cache is not None:
            self._cache = cache
        elif cfg.cache.url:
            from pykour.cache.valkey import ValkeyStorage

            self._cache = ValkeyStorage(
                url=cfg.cache.url,
                prefix=cfg.cache.prefix,
            )
        else:
            self._cache = None

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

        # Resolve OpenAPI settings (code > config file)
        # Use sentinel check to distinguish "not specified" from "explicitly None"
        resolved_title = title if title is not None else cfg.openapi.title
        resolved_version = version if version is not None else cfg.openapi.version
        resolved_description = (
            description if description is not None else cfg.openapi.description
        )
        resolved_docs_url: str | None = (
            cfg.openapi.docs_url
            if docs_url is _USE_CONFIG_DEFAULT
            else cast("str | None", docs_url)
        )
        resolved_openapi_url: str | None = (
            cfg.openapi.openapi_url
            if openapi_url is _USE_CONFIG_DEFAULT
            else cast("str | None", openapi_url)
        )
        resolved_redoc_url: str | None = (
            cfg.openapi.redoc_url
            if redoc_url is _USE_CONFIG_DEFAULT
            else cast("str | None", redoc_url)
        )

        # Set up OpenAPI documentation
        self._openapi_config = OpenAPIConfig(
            title=resolved_title,
            version=resolved_version,
            description=resolved_description,
            docs_url=resolved_docs_url,
            openapi_url=resolved_openapi_url,
            redoc_url=resolved_redoc_url,
        )
        self._openapi_handler: OpenAPIRouteHandler | None = None
        if resolved_docs_url or resolved_openapi_url or resolved_redoc_url:
            self._openapi_handler = setup_openapi(self, self._openapi_config)

        # Resolve health check settings (code > config file)
        # Use sentinel check to distinguish "not specified" from "explicitly None"
        resolved_health_url: str | None = (
            cfg.health.url
            if health_url is _USE_CONFIG_DEFAULT
            else cast("str | None", health_url)
        )

        # Set up health check endpoint
        self._health_config = HealthCheckConfig(health_url=resolved_health_url)
        self._health_handler: HealthCheckHandler | None = None
        if resolved_health_url is not None:
            self._health_handler = setup_health_check(self._health_config)

        # Resolve metrics settings (code > config file)
        # Use sentinel check to distinguish "not specified" from "explicitly None"
        resolved_metrics_url: str | None = (
            cfg.metrics.url
            if metrics_url is _USE_CONFIG_DEFAULT
            else cast("str | None", metrics_url)
        )

        # Set up metrics endpoint
        # Build exclude paths list
        metrics_exclude_paths = ["/metrics"]
        if resolved_health_url is not None:
            metrics_exclude_paths.append(resolved_health_url)
        if resolved_metrics_url is not None and resolved_metrics_url != "/metrics":
            metrics_exclude_paths.append(resolved_metrics_url)

        self._metrics_config = MetricsConfig(
            metrics_url=resolved_metrics_url,
            exclude_paths=metrics_exclude_paths,
        )
        self._metrics_collector: MetricsCollector | None = None
        self._metrics_handler: MetricsHandler | None = None
        if resolved_metrics_url is not None:
            self._metrics_collector = MetricsCollector(
                buckets=self._metrics_config.latency_buckets
            )
            self._metrics_handler = setup_metrics(
                self._metrics_config, self._metrics_collector
            )

        # Auto-configure middleware from config file
        self._configure_middleware_from_config()

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

    async def _startup(self) -> None:
        """Perform startup tasks.

        This method is thread-safe and uses double-checked locking to prevent
        race conditions when multiple concurrent requests trigger auto-start.
        """
        # Fast path: already started
        if self._started:
            return

        async with self._startup_lock:
            # Re-check after acquiring lock (double-checked locking)
            if self._started:
                return

            # Build middleware stack during startup for thread safety
            if self._app is None:
                self._app = self._build_middleware_stack()
            if self._database is not None:
                await self._database.connect()
            if self._cache is not None:
                await self._cache.connect()
            self._started = True

    async def _shutdown(self) -> None:
        """Perform shutdown tasks."""
        if not self._started:
            return
        if self._database is not None:
            await self._database.disconnect()
        if self._cache is not None:
            await self._cache.disconnect()
        self._started = False

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
        self._middleware_stack.append((middleware_class, options))

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
            self._middleware_stack.append((FunctionMiddleware, {"dispatch": fn}))
            return fn

        if func is not None:
            return decorator(func)
        return decorator

    def _configure_middleware_from_config(self) -> None:
        """Configure middleware based on config file settings.

        Automatically adds middleware when enabled in the configuration file.
        Middleware is added in a specific order to ensure correct behavior.
        """
        mw_config = self._pykour_config.middleware

        # Trace middleware (should be outermost for proper trace ID propagation)
        if mw_config.trace.enabled:
            from pykour.middleware import TraceMiddleware

            self.add_middleware(TraceMiddleware)

        # Logging middleware
        if mw_config.logging.enabled:
            from pykour.middleware import LoggingMiddleware

            self.add_middleware(
                LoggingMiddleware,
                logger_name=mw_config.logging.logger_name,
                level=mw_config.logging.level,
                exclude_paths=mw_config.logging.exclude_paths,
                log_request_headers=mw_config.logging.log_request_headers,
                log_response_headers=mw_config.logging.log_response_headers,
            )

        # Security Headers middleware
        if mw_config.security.enabled:
            from pykour.middleware import (
                ContentSecurityPolicy,
                SecurityHeadersMiddleware,
            )

            csp = None
            if mw_config.security.csp:
                csp = ContentSecurityPolicy(
                    default_src=mw_config.security.csp.default_src,
                    script_src=mw_config.security.csp.script_src,
                    style_src=mw_config.security.csp.style_src,
                    img_src=mw_config.security.csp.img_src,
                    font_src=mw_config.security.csp.font_src,
                    connect_src=mw_config.security.csp.connect_src,
                    media_src=mw_config.security.csp.media_src,
                    object_src=mw_config.security.csp.object_src,
                    frame_src=mw_config.security.csp.frame_src,
                    frame_ancestors=mw_config.security.csp.frame_ancestors,
                    form_action=mw_config.security.csp.form_action,
                    base_uri=mw_config.security.csp.base_uri,
                )
            self.add_middleware(
                SecurityHeadersMiddleware,
                hsts_max_age=mw_config.security.hsts_max_age,
                hsts_include_subdomains=mw_config.security.hsts_include_subdomains,
                hsts_preload=mw_config.security.hsts_preload,
                x_content_type_options=mw_config.security.x_content_type_options,
                x_frame_options=mw_config.security.x_frame_options,
                x_xss_protection=mw_config.security.x_xss_protection,
                referrer_policy=mw_config.security.referrer_policy,
                content_security_policy=csp,
                csp_report_only=mw_config.security.csp_report_only,
                exclude_paths=mw_config.security.exclude_paths,
            )

        # CORS middleware
        if mw_config.cors.enabled:
            from pykour.middleware import CORSMiddleware

            self.add_middleware(
                CORSMiddleware,
                allow_origins=mw_config.cors.allow_origins,
                allow_methods=mw_config.cors.allow_methods,
                allow_headers=mw_config.cors.allow_headers,
                allow_credentials=mw_config.cors.allow_credentials,
                expose_headers=mw_config.cors.expose_headers,
                max_age=mw_config.cors.max_age,
            )

        # CSRF middleware
        if mw_config.csrf.enabled:
            from pykour.middleware import CSRFMiddleware

            self.add_middleware(
                CSRFMiddleware,
                cookie_name=mw_config.csrf.cookie_name,
                header_name=mw_config.csrf.header_name,
                cookie_path=mw_config.csrf.cookie_path,
                cookie_domain=mw_config.csrf.cookie_domain,
                cookie_secure=mw_config.csrf.cookie_secure,
                cookie_httponly=mw_config.csrf.cookie_httponly,
                cookie_samesite=mw_config.csrf.cookie_samesite,
                cookie_max_age=mw_config.csrf.cookie_max_age,
                exclude_paths=mw_config.csrf.exclude_paths,
            )

        # Rate Limiting middleware
        if mw_config.rate_limit.enabled:
            from pykour.middleware import RateLimitConfig, RateLimitMiddleware

            path_configs = {
                path: RateLimitConfig(cfg.requests_per_second, cfg.burst_size)
                for path, cfg in mw_config.rate_limit.path_configs.items()
            }
            self.add_middleware(
                RateLimitMiddleware,
                requests_per_second=mw_config.rate_limit.requests_per_second,
                burst_size=mw_config.rate_limit.burst_size,
                exclude_paths=mw_config.rate_limit.exclude_paths,
                include_headers=mw_config.rate_limit.include_headers,
                path_configs=path_configs if path_configs else None,
            )

        # Request Size Limit middleware
        if mw_config.size_limit.enabled:
            from pykour.middleware import RequestSizeLimitMiddleware

            self.add_middleware(
                RequestSizeLimitMiddleware,
                max_size=mw_config.size_limit.max_size,
                max_size_by_content_type=mw_config.size_limit.max_size_by_content_type
                or None,
                exclude_paths=mw_config.size_limit.exclude_paths,
                check_content_length=mw_config.size_limit.check_content_length,
                check_body_size=mw_config.size_limit.check_body_size,
            )

        # JWT Auth middleware (should be one of the innermost)
        if mw_config.jwt.enabled:
            from pykour.middleware import JWTAuthMiddleware

            if not mw_config.jwt.secret_key and not mw_config.jwt.secret_keys:
                raise ValueError(
                    "JWT middleware enabled but no secret_key configured. "
                    "Set middleware.jwt.secret_key in pykour.toml or "
                    "PYKOUR_JWT_SECRET_KEY environment variable."
                )
            self.add_middleware(
                JWTAuthMiddleware,
                secret_key=mw_config.jwt.secret_key,
                secret_keys=mw_config.jwt.secret_keys,
                algorithm=mw_config.jwt.algorithm,
                exclude_paths=mw_config.jwt.exclude_paths,
                auto_error=mw_config.jwt.auto_error,
            )

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
        app: Any = self._core_asgi_app

        # Apply middleware in reverse order so first added is outermost
        for middleware_class, options in reversed(self._middleware_stack):
            app = middleware_class(app, **options)

        return app

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

        response = await self._handle_request(scope, receive)
        await response(scope, receive, send)

    async def _handle_request(self, scope: Scope, receive: Receive) -> Response:
        """Find and execute the appropriate route handler."""
        path = scope.get("path", "/")
        method = scope.get("method", "GET")

        handler, path_params = self._router.match(path, method)

        # Automatic HEAD support: use GET handler if HEAD is not explicitly defined
        is_auto_head = False
        if handler is None and method == "HEAD":
            handler, path_params = self._router.match(path, "GET")
            is_auto_head = handler is not None

        if handler is not None:
            request = Request(scope, receive, path_params)

            try:
                kwargs = await self._injector.inject(handler, request, path_params)

                # Check for @cache decorator and try to serve from cache
                from pykour.cache.decorators import get_cache_info, get_cache_evict_info
                from pykour.conditional import get_etag_info, get_last_modified_info
                from pykour.core.handler import (
                    check_etag_match,
                    compute_etag,
                    extract_last_modified,
                    format_last_modified,
                    parse_if_modified_since,
                )

                cache_infos = get_cache_info(handler)
                etag_infos = get_etag_info(handler)
                last_modified_infos = get_last_modified_info(handler)
                cache_key: str | None = None

                if cache_infos and self._cache is not None:
                    cache_info = cache_infos[0]  # Use first cache decorator
                    cache_key = interpolate_cache_key(cache_info.key, kwargs)
                    cached_data = await self._cache.get(cache_key)
                    if cached_data is not None:
                        cached_response = deserialize_response(cached_data)

                        # Check ETag on cache hit (returns 304 without handler execution)
                        if etag_infos:
                            etag_info = etag_infos[0]
                            computed_etag = compute_etag(
                                cached_response.body,
                                weak=etag_info.weak,
                                algorithm=etag_info.algorithm,
                            )
                            if_none_match = request.headers.get("if-none-match")
                            if if_none_match and check_etag_match(
                                if_none_match, computed_etag
                            ):
                                # Return 304 Not Modified (no body)
                                return Response(
                                    content=b"",
                                    status_code=304,
                                    headers={"ETag": computed_etag},
                                )
                            # Add ETag to cached response
                            cached_response.set_header("ETag", computed_etag)

                        return cached_response

                # Execute handler
                result = handler(**kwargs)
                if inspect.isawaitable(result):
                    response = cast(Response, await result)
                else:
                    response = cast(Response, result)

                # Apply declarative status code if response uses default (200)
                from pykour.status_code import (
                    get_default_status_code,
                    get_method_default_status_code,
                )

                declared_status = get_default_status_code(handler)
                if declared_status is not None and response.status_code == 200:
                    response.status_code = declared_status
                elif response.status_code == 200:
                    # Apply method-based default when no decorator
                    response.status_code = get_method_default_status_code(method)

                # Apply declarative headers from @header decorator
                from pykour.header import get_header_info

                header_infos = get_header_info(handler)
                for header_info in header_infos:
                    # Check condition (e.g., on_status)
                    if header_info.condition is not None and not header_info.condition(
                        response.status_code
                    ):
                        continue

                    # Interpolate header value
                    header_value = interpolate_header_value(
                        header_info.value_template, kwargs, response
                    )
                    if header_value is not None:
                        response.add_header(header_info.name, header_value)

                # Handle @etag decorator (after handler execution)
                computed_etag: str | None = None
                if etag_infos:
                    etag_info = etag_infos[0]
                    computed_etag = compute_etag(
                        response.body,
                        weak=etag_info.weak,
                        algorithm=etag_info.algorithm,
                    )
                    response.set_header("ETag", computed_etag)

                    # Check If-None-Match header
                    if_none_match = request.headers.get("if-none-match")
                    if if_none_match and check_etag_match(if_none_match, computed_etag):
                        # Return 304 Not Modified (no body)
                        return Response(
                            content=b"",
                            status_code=304,
                            headers={"ETag": computed_etag},
                        )

                # Handle @last_modified decorator
                if last_modified_infos:
                    lm_info = last_modified_infos[0]
                    last_mod_time = extract_last_modified(
                        response,
                        lm_info.static_value,
                        lm_info.response_field,
                        lm_info.format,
                    )

                    if last_mod_time:
                        lm_header = format_last_modified(last_mod_time)
                        response.set_header("Last-Modified", lm_header)

                        # Check If-Modified-Since header
                        if_modified_since = request.headers.get("if-modified-since")
                        if if_modified_since:
                            ims_time = parse_if_modified_since(if_modified_since)
                            if ims_time and last_mod_time <= ims_time:
                                # Return 304 Not Modified (no body)
                                headers_304: dict[str, str] = {
                                    "Last-Modified": lm_header
                                }
                                if computed_etag:
                                    headers_304["ETag"] = computed_etag
                                return Response(
                                    content=b"",
                                    status_code=304,
                                    headers=headers_304,
                                )

                # Cache response if @cache decorator is present
                if cache_infos and self._cache is not None and cache_key is not None:
                    cache_info = cache_infos[0]
                    # Only cache successful responses (2xx)
                    if 200 <= response.status_code < 300:
                        serialized = serialize_response(response)
                        await self._cache.set(cache_key, serialized, cache_info.ttl)

                # Handle @cache_evict decorator
                evict_infos = get_cache_evict_info(handler)
                if evict_infos and self._cache is not None:
                    for evict_info in evict_infos:
                        evict_key = interpolate_cache_key(evict_info.key, kwargs)
                        if evict_info.all_entries:
                            await self._cache.delete_pattern(evict_key)
                        else:
                            await self._cache.delete(evict_key)

                # For automatic HEAD, return headers only (empty body)
                if is_auto_head:
                    return Response(
                        content=b"",
                        status_code=response.status_code,
                        headers=response.headers,
                        media_type=response.media_type,
                    )

                return response
            except Exception as e:
                return await self._handle_exception(request, e)

        # Check if path exists but method is not allowed
        allowed_methods = self._router.get_allowed_methods(path)
        if allowed_methods:
            # RFC 7231: Allow header should list permitted methods (normalized to uppercase)
            allow_header = ", ".join(sorted(m.upper() for m in allowed_methods))
            return JSONResponse(
                content={"error": "Method Not Allowed"},
                status_code=405,
                headers={"Allow": allow_header},
            )

        # Not found
        return JSONResponse(
            content={"error": "Not Found"},
            status_code=404,
        )

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
            await self._handle_lifespan(scope, receive, send)
            return

        # Auto-start if not started (for testing without lifespan)
        # Always call _startup() which handles double-checked locking internally
        # to avoid TOCTOU race between checking self._started and calling _startup()
        await self._startup()

        if scope["type"] == "http":
            await self._app(scope, receive, send)
        elif scope["type"] == "websocket":
            await self._handle_websocket(scope, receive, send)

    async def _handle_lifespan(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        """Handle ASGI lifespan events."""
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                try:
                    await self._startup()
                    await send({"type": "lifespan.startup.complete"})
                except Exception as e:
                    await send({"type": "lifespan.startup.failed", "message": str(e)})
                    return
            elif message["type"] == "lifespan.shutdown":
                try:
                    await self._shutdown()
                    await send({"type": "lifespan.shutdown.complete"})
                except Exception:
                    await send({"type": "lifespan.shutdown.complete"})
                return

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
