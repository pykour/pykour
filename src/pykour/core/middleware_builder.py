"""Middleware stack builder for Pykour application."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from pykour.middleware import BaseMiddleware, FunctionMiddleware, MiddlewareFunc

if TYPE_CHECKING:
    from pykour.config.models import MiddlewareConfig


class MiddlewareBuilder:
    """Builds middleware stack from configuration and programmatic additions.

    This class handles:
    - Middleware configuration from config file
    - Programmatic middleware addition
    - Building the final middleware stack wrapping the core app
    """

    def __init__(self, config: "MiddlewareConfig | None" = None) -> None:
        """Initialize middleware builder.

        Args:
            config: Optional middleware configuration from config file.
        """
        self._config = config
        self._stack: list[tuple[type[BaseMiddleware], dict[str, Any]]] = []

    @property
    def stack(self) -> list[tuple[type[BaseMiddleware], dict[str, Any]]]:
        """Get the current middleware stack."""
        return self._stack

    def add(
        self,
        middleware_class: type[BaseMiddleware],
        **options: Any,
    ) -> None:
        """Add middleware to the stack.

        Middleware is executed in the order it is added, with the first
        middleware being the outermost wrapper.

        Args:
            middleware_class: The middleware class to add.
            **options: Options to pass to the middleware constructor.
        """
        self._stack.append((middleware_class, options))

    def add_function(self, func: MiddlewareFunc) -> None:
        """Add function-based middleware to the stack.

        Args:
            func: The middleware function to add.
        """
        self._stack.append((FunctionMiddleware, {"dispatch": func}))

    def configure_from_config(self) -> None:
        """Configure middleware based on config file settings.

        Automatically adds middleware when enabled in the configuration file.
        Middleware is added in a specific order to ensure correct behavior.
        """
        if self._config is None:
            return

        mw_config = self._config

        # Trace middleware (should be outermost for proper trace ID propagation)
        if mw_config.trace.enabled:
            self._configure_trace()

        # Logging middleware
        if mw_config.logging.enabled:
            self._configure_logging(mw_config)

        # Security Headers middleware
        if mw_config.security.enabled:
            self._configure_security(mw_config)

        # CORS middleware
        if mw_config.cors.enabled:
            self._configure_cors(mw_config)

        # CSRF middleware
        if mw_config.csrf.enabled:
            self._configure_csrf(mw_config)

        # Rate Limiting middleware
        if mw_config.rate_limit.enabled:
            self._configure_rate_limit(mw_config)

        # Request Size Limit middleware
        if mw_config.size_limit.enabled:
            self._configure_size_limit(mw_config)

        # JWT Auth middleware (should be one of the innermost)
        if mw_config.jwt.enabled:
            self._configure_jwt(mw_config)

    def _configure_trace(self) -> None:
        """Configure trace middleware."""
        from pykour.middleware import TraceMiddleware

        self.add(TraceMiddleware)

    def _configure_logging(self, mw_config: "MiddlewareConfig") -> None:
        """Configure logging middleware."""
        from pykour.middleware import LoggingMiddleware

        self.add(
            LoggingMiddleware,
            logger_name=mw_config.logging.logger_name,
            level=mw_config.logging.level,
            exclude_paths=mw_config.logging.exclude_paths,
            log_request_headers=mw_config.logging.log_request_headers,
            log_response_headers=mw_config.logging.log_response_headers,
        )

    def _configure_security(self, mw_config: "MiddlewareConfig") -> None:
        """Configure security headers middleware."""
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

        self.add(
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

    def _configure_cors(self, mw_config: "MiddlewareConfig") -> None:
        """Configure CORS middleware."""
        from pykour.middleware import CORSMiddleware

        self.add(
            CORSMiddleware,
            allow_origins=mw_config.cors.allow_origins,
            allow_methods=mw_config.cors.allow_methods,
            allow_headers=mw_config.cors.allow_headers,
            allow_credentials=mw_config.cors.allow_credentials,
            expose_headers=mw_config.cors.expose_headers,
            max_age=mw_config.cors.max_age,
        )

    def _configure_csrf(self, mw_config: "MiddlewareConfig") -> None:
        """Configure CSRF middleware."""
        from pykour.middleware import CSRFMiddleware

        self.add(
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

    def _configure_rate_limit(self, mw_config: "MiddlewareConfig") -> None:
        """Configure rate limit middleware."""
        from pykour.middleware import RateLimitConfig, RateLimitMiddleware

        path_configs = {
            path: RateLimitConfig(cfg.requests_per_second, cfg.burst_size)
            for path, cfg in mw_config.rate_limit.path_configs.items()
        }

        self.add(
            RateLimitMiddleware,
            requests_per_second=mw_config.rate_limit.requests_per_second,
            burst_size=mw_config.rate_limit.burst_size,
            exclude_paths=mw_config.rate_limit.exclude_paths,
            include_headers=mw_config.rate_limit.include_headers,
            path_configs=path_configs if path_configs else None,
        )

    def _configure_size_limit(self, mw_config: "MiddlewareConfig") -> None:
        """Configure request size limit middleware."""
        from pykour.middleware import RequestSizeLimitMiddleware

        self.add(
            RequestSizeLimitMiddleware,
            max_size=mw_config.size_limit.max_size,
            max_size_by_content_type=mw_config.size_limit.max_size_by_content_type
            or None,
            exclude_paths=mw_config.size_limit.exclude_paths,
            check_content_length=mw_config.size_limit.check_content_length,
            check_body_size=mw_config.size_limit.check_body_size,
        )

    def _configure_jwt(self, mw_config: "MiddlewareConfig") -> None:
        """Configure JWT auth middleware."""
        from pykour.middleware import JWTAuthMiddleware

        if not mw_config.jwt.secret_key and not mw_config.jwt.secret_keys:
            raise ValueError(
                "JWT middleware enabled but no secret_key configured. "
                "Set middleware.jwt.secret_key in pykour.toml or "
                "PYKOUR_JWT_SECRET_KEY environment variable."
            )

        self.add(
            JWTAuthMiddleware,
            secret_key=mw_config.jwt.secret_key,
            secret_keys=mw_config.jwt.secret_keys,
            algorithm=mw_config.jwt.algorithm,
            exclude_paths=mw_config.jwt.exclude_paths,
            auto_error=mw_config.jwt.auto_error,
        )

    def build(self, core_app: Any) -> Any:
        """Build the middleware stack wrapping the core app.

        Args:
            core_app: The core ASGI application to wrap.

        Returns:
            The wrapped ASGI application with all middleware applied.
        """
        app: Any = core_app

        # Apply middleware in reverse order so first added is outermost
        for middleware_class, options in reversed(self._stack):
            app = middleware_class(app, **options)

        return app


def create_middleware_decorator(
    builder: MiddlewareBuilder,
) -> Callable[
    [MiddlewareFunc | None], Callable[[MiddlewareFunc], MiddlewareFunc] | MiddlewareFunc
]:
    """Create a middleware decorator function.

    Args:
        builder: The middleware builder to add middleware to.

    Returns:
        A decorator that can be used with or without parentheses.
    """

    def middleware(
        func: MiddlewareFunc | None = None,
    ) -> Callable[[MiddlewareFunc], MiddlewareFunc] | MiddlewareFunc:
        """Decorator to add function-based middleware.

        Can be used with or without parentheses.
        """

        def decorator(fn: MiddlewareFunc) -> MiddlewareFunc:
            builder.add_function(fn)
            return fn

        if func is not None:
            return decorator(func)
        return decorator

    return middleware
