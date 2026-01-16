"""Pykour ASGI Application."""

from __future__ import annotations

import asyncio
import inspect
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, cast

from pykour import json as pykour_json
from pykour.exception_handlers import ExceptionHandler, ExceptionHandlerRegistry
from pykour.exceptions import HTTPException
from pykour.injection import ParameterInjector
from pykour.middleware import BaseMiddleware, FunctionMiddleware, MiddlewareFunc
from pykour.openapi.config import OpenAPIConfig
from pykour.openapi.routes import OpenAPIRouteHandler, setup_openapi
from pykour.request import Request
from pykour.response import JSONResponse, Response
from pykour.router import Router
from pykour.schema import ValidationError
from pykour.types import Receive, Scope, Send
from pykour.di import ServiceContainer

if TYPE_CHECKING:
    from pykour.cache.storage import CacheStorage
    from pykour.db import Database
    from pykour.websocket import WebSocket


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
        routes_dir: str | Path = "routes",
        database: "Database | None" = None,
        cache: "CacheStorage | None" = None,
        debug: bool | None = None,
        *,
        title: str = "Pykour API",
        version: str = "1.0.0",
        description: str | None = None,
        docs_url: str | None = "/docs",
        openapi_url: str | None = "/openapi.json",
        redoc_url: str | None = "/redoc",
    ) -> None:
        """Initialize Pykour application.

        Args:
            routes_dir: Directory containing route.py files.
            database: Optional database instance for dependency injection.
            cache: Optional cache storage for response and data caching.
            debug: Enable debug mode for detailed error tracebacks.
                   If None, reads from PYKOUR_DEBUG environment variable.
            title: API title for OpenAPI documentation.
            version: API version for OpenAPI documentation.
            description: API description for OpenAPI documentation.
            docs_url: URL path for Swagger UI. Set to None to disable.
            openapi_url: URL path for OpenAPI JSON schema. Set to None to disable.
            redoc_url: URL path for ReDoc. Set to None to disable.
        """
        import os

        self._router = Router(routes_dir)
        self._database = database
        self._cache = cache
        self._started = False
        self._startup_lock = asyncio.Lock()
        self._middleware_stack: list[tuple[type[BaseMiddleware], dict[str, Any]]] = []
        self._app: Any = None
        self._services = ServiceContainer()

        # Determine debug mode
        if debug is None:
            self._debug = os.environ.get("PYKOUR_DEBUG", "").lower() in (
                "1",
                "true",
                "yes",
            )
        else:
            self._debug = debug

        # Auto-register database in service container for DI
        if self._database is not None:
            from pykour.db.database import Database

            self._services.register_instance(Database, self._database)

        # Auto-register cache client in service container for DI
        if self._cache is not None:
            from pykour.cache.client import Cache

            cache_client = Cache(self._cache)
            self._services.register_instance(Cache, cache_client)

        # Initialize exception handler registry with default handlers
        self._exception_handlers = ExceptionHandlerRegistry()
        self._exception_handlers.add(HTTPException, self._handle_http_exception)
        self._exception_handlers.add(ValidationError, self._handle_validation_exception)

        # Initialize parameter injector
        self._injector = ParameterInjector(self._services, self._database)

        # Set up OpenAPI documentation
        self._openapi_config = OpenAPIConfig(
            title=title,
            version=version,
            description=description,
            docs_url=docs_url,
            openapi_url=openapi_url,
            redoc_url=redoc_url,
        )
        self._openapi_handler: OpenAPIRouteHandler | None = None
        if docs_url or openapi_url or redoc_url:
            self._openapi_handler = setup_openapi(self, self._openapi_config)

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
        # Check OpenAPI routes first
        if self._openapi_handler is not None:
            if await self._openapi_handler.handle(scope, receive, send):
                return

        response = await self._handle_request(scope, receive)
        await response(scope, receive, send)

    def _interpolate_cache_key(self, template: str, kwargs: dict[str, Any]) -> str:
        """Interpolate {param} placeholders in cache key template.

        Args:
            template: Key template with {param} placeholders.
            kwargs: Handler kwargs for interpolation.

        Returns:
            Interpolated cache key.

        Example:
            template = "user:{id}:profile"
            kwargs = {"id": 123, "request": ...}
            result = "user:123:profile"
        """
        import re

        def replace(match: re.Match[str]) -> str:
            param_name = match.group(1)
            if param_name in kwargs:
                return str(kwargs[param_name])
            raise ValueError(f"Cache key references unknown parameter: {param_name}")

        return re.sub(r"\{(\w+)\}", replace, template)

    def _interpolate_header_value(
        self,
        template: str,
        kwargs: dict[str, Any],
        response: Response,
    ) -> str | None:
        """Interpolate {param} placeholders in header value template.

        Args:
            template: Value template with {param} or {param.field} placeholders.
            kwargs: Handler kwargs for interpolation.
            response: Response object for response body interpolation.

        Returns:
            Interpolated value, or None if interpolation failed.

        Example:
            template = "/users/{id}"
            kwargs = {"id": 123}
            result = "/users/123"

            # With response body
            template = "/users/{id}"
            kwargs = {}
            response.body = b'{"id": 456}'
            result = "/users/456"
        """
        import re

        def get_value(param_path: str) -> str | None:
            """Get value for a parameter path (supports dot notation)."""
            parts = param_path.split(".")

            # First, try to resolve from kwargs
            if parts[0] in kwargs:
                value = kwargs[parts[0]]
                for part in parts[1:]:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    elif hasattr(value, part):
                        value = getattr(value, part)
                    else:
                        return None
                return str(value)

            # Then, try to resolve from response body
            if hasattr(response, "body") and response.body:
                try:
                    data = pykour_json.loads(response.body)
                    for part in parts:
                        if isinstance(data, dict) and part in data:
                            data = data[part]
                        else:
                            return None
                    return str(data)
                except Exception:
                    pass

            return None

        def replace(match: re.Match[str]) -> str:
            param_path = match.group(1)
            value = get_value(param_path)
            if value is not None:
                return value
            # If value not found, keep the original placeholder
            return match.group(0)

        result = re.sub(r"\{([^}]+)\}", replace, template)
        # Return None if any placeholder was not resolved
        if "{" in result:
            return None
        return result

    def _serialize_response(self, response: Response) -> bytes:
        """Serialize a Response object for caching.

        Args:
            response: Response to serialize.

        Returns:
            Serialized response as bytes.
        """
        data = {
            "status_code": response.status_code,
            "headers": response.headers,
            "body": response.body.decode("utf-8"),
            "media_type": response.media_type,
        }
        return pykour_json.dumps(data)

    def _deserialize_response(self, data: bytes) -> Response:
        """Deserialize cached bytes to a Response object.

        Args:
            data: Cached response bytes.

        Returns:
            Reconstructed Response object.
        """
        parsed = pykour_json.loads(data)
        return Response(
            content=parsed["body"],
            status_code=parsed["status_code"],
            headers=parsed["headers"],
            media_type=parsed.get("media_type"),
        )

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

                cache_infos = get_cache_info(handler)
                cache_key: str | None = None

                if cache_infos and self._cache is not None:
                    cache_info = cache_infos[0]  # Use first cache decorator
                    cache_key = self._interpolate_cache_key(cache_info.key, kwargs)
                    cached_data = await self._cache.get(cache_key)
                    if cached_data is not None:
                        return self._deserialize_response(cached_data)

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
                    header_value = self._interpolate_header_value(
                        header_info.value_template, kwargs, response
                    )
                    if header_value is not None:
                        response.add_header(header_info.name, header_value)

                # Cache response if @cache decorator is present
                if cache_infos and self._cache is not None and cache_key is not None:
                    cache_info = cache_infos[0]
                    # Only cache successful responses (2xx)
                    if 200 <= response.status_code < 300:
                        serialized = self._serialize_response(response)
                        await self._cache.set(cache_key, serialized, cache_info.ttl)

                # Handle @cache_evict decorator
                evict_infos = get_cache_evict_info(handler)
                if evict_infos and self._cache is not None:
                    for evict_info in evict_infos:
                        evict_key = self._interpolate_cache_key(evict_info.key, kwargs)
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

        Looks up a registered handler for the exception type (checking MRO).
        If no handler is found, uses the default fallback handler.

        Args:
            request: The request object.
            exc: The exception that was raised.

        Returns:
            Response from the exception handler.
        """
        handler = self._exception_handlers.get(exc)
        if handler is not None:
            result = handler(request, exc)
            if inspect.isawaitable(result):
                return cast(Response, await result)
            return cast(Response, result)

        # No registered handler - use fallback
        return self._handle_unhandled_exception(exc)

    def _handle_http_exception(self, request: Request, exc: HTTPException) -> Response:
        """Default handler for HTTPException.

        Args:
            request: The request object.
            exc: The HTTP exception that was raised.

        Returns:
            JSON response with error details.
        """
        content: dict[str, Any] = {"error": exc.detail}

        # Convert headers dict to proper format
        headers: dict[str, str] = {}
        if exc.headers:
            headers.update(exc.headers)

        return JSONResponse(
            content=content,
            status_code=exc.status_code,
            headers=headers,
        )

    def _handle_validation_exception(
        self, request: Request, exc: ValidationError
    ) -> Response:
        """Default handler for ValidationError.

        Args:
            request: The request object.
            exc: The validation exception that was raised.

        Returns:
            JSON response with validation error details.
        """
        return JSONResponse(
            content=exc.to_dict(),
            status_code=422,
        )

    def _handle_unhandled_exception(self, exc: Exception) -> Response:
        """Handle exceptions with no registered handler.

        Args:
            exc: The exception that was raised.

        Returns:
            JSON response with error details (verbose in debug mode).
        """
        import logging
        import traceback

        logger = logging.getLogger("pykour")

        if self._debug:
            # In debug mode, show full traceback
            tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
            tb_str = "".join(tb_lines)
            logger.error(f"Unhandled exception:\n{tb_str}")

            return JSONResponse(
                content={
                    "error": "Internal Server Error",
                    "detail": str(exc),
                    "type": type(exc).__name__,
                    "traceback": tb_lines,
                },
                status_code=500,
            )
        else:
            # In production, log the error but return generic message
            logger.exception("Unhandled exception during request processing")
            return JSONResponse(
                content={"error": "Internal Server Error"},
                status_code=500,
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

        Args:
            scope: ASGI WebSocket scope.
            receive: ASGI receive callable.
            send: ASGI send callable.
        """
        import logging

        from pykour.websocket import WebSocket, WebSocketDisconnect, WebSocketState

        logger = logging.getLogger("pykour")
        path = scope.get("path", "/")
        handler, path_params = self._router.match(path, "WEBSOCKET")

        if handler is None:
            # No WebSocket handler found - close with 4004 (not found)
            await send(
                {
                    "type": "websocket.close",
                    "code": 4004,
                    "reason": "Not Found",
                }
            )
            return

        ws = WebSocket(scope, receive, send, path_params)

        try:
            # Inject parameters (WebSocket instance and path params)
            kwargs = await self._inject_websocket_params(handler, ws, path_params)

            result = handler(**kwargs)
            if inspect.isawaitable(result):
                await result
        except WebSocketDisconnect:
            pass  # Normal disconnect
        except Exception as e:
            logger.exception(f"WebSocket error: {e}")

            if ws.state != WebSocketState.DISCONNECTED:
                try:
                    await ws.close(code=1011, reason="Internal Error")
                except Exception:
                    pass  # Connection may already be closed

    async def _inject_websocket_params(
        self,
        handler: Callable[..., Any],
        ws: "WebSocket",
        path_params: dict[str, str],
    ) -> dict[str, Any]:
        """Inject parameters for WebSocket handler.

        Supports:
        - WebSocket instance (ws parameter or by type annotation)
        - Path parameters
        - Service dependencies via Depends()

        Args:
            handler: The WebSocket handler function.
            ws: The WebSocket connection instance.
            path_params: Path parameters extracted from URL.

        Returns:
            Dictionary of keyword arguments for the handler.
        """
        from typing import get_type_hints

        from pykour.di import Depends as DIDepends
        from pykour.schema.fields import Path as PathParam
        from pykour.schema.parser import coerce_path_param
        from pykour.websocket import WebSocket as WebSocketClass

        try:
            hints = get_type_hints(handler)
        except Exception:
            hints = {}

        sig = inspect.signature(handler)
        kwargs: dict[str, Any] = {}

        for param_name, param in sig.parameters.items():
            param_type = hints.get(param_name, Any)
            default = param.default

            # WebSocket instance injection (by type or by name)
            if param_type is WebSocketClass or param_name == "ws":
                kwargs[param_name] = ws

            # Service dependency injection
            elif isinstance(default, DIDepends):
                service = self._injector.inject_service_depends(
                    param_name, param_type, default
                )
                kwargs[param_name] = service

            # Path parameter with explicit marker
            elif isinstance(default, PathParam):
                kwargs[param_name] = self._injector.inject_path_param(
                    param_name, param_type, default, path_params
                )

            # Path parameter by convention (name matches)
            elif param_name in path_params:
                kwargs[param_name] = coerce_path_param(
                    path_params[param_name], param_name, param_type
                )

            # Default value
            elif param.default is not inspect.Parameter.empty:
                kwargs[param_name] = param.default

        return kwargs
