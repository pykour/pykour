"""ASGI middleware for setting policy context from requests."""

from __future__ import annotations

import inspect
import types
from typing import Any, Awaitable, Callable

from pykour.db.access_policy.context import clear_policy_context, set_policy_context

# Type aliases for ASGI
Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


class AccessPolicyMiddleware:
    """ASGI middleware that sets policy context from request.

    This middleware extracts authentication/authorization information from
    incoming requests and sets the policy context for database queries.

    Example:
        from pykour import Pykour
        from pykour.db import Database
        from pykour.db.access_policy import AccessPolicyMiddleware

        db = Database("postgresql://localhost/myapp")
        app = Pykour(routes_dir="routes", database=db)

        # Wrap with access policy middleware
        app = AccessPolicyMiddleware(
            app,
            tenant_extractor=lambda req: req.headers.get("X-Tenant-ID"),
            user_extractor=lambda req: getattr(req.state, "user_id", None),
            roles_extractor=lambda req: getattr(req.state, "roles", []),
        )

    Extractors can be:
    - Sync functions: `lambda req: req.headers.get("X-Tenant-ID")`
    - Async functions: `async def get_tenant(req): ...`
    """

    def __init__(
        self,
        app: Any,
        *,
        tenant_extractor: Callable[[Any], Any] | None = None,
        user_extractor: Callable[[Any], Any] | None = None,
        organization_extractor: Callable[[Any], Any] | None = None,
        roles_extractor: Callable[[Any], list[str] | None] | None = None,
        custom_extractors: dict[str, Callable[[Any], Any]] | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application to wrap.
            tenant_extractor: Function to extract tenant_id from request.
            user_extractor: Function to extract user_id from request.
            organization_extractor: Function to extract organization_id from request.
            roles_extractor: Function to extract roles list from request.
            custom_extractors: Dict of custom extractors {key: extractor_func}.
        """
        self.app = app
        self.tenant_extractor = tenant_extractor
        self.user_extractor = user_extractor
        self.organization_extractor = organization_extractor
        self.roles_extractor = roles_extractor
        self.custom_extractors = custom_extractors or {}

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle an ASGI request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Build a minimal request-like object for extractors
        request = _ScopeWrapper(scope)

        # Extract policy context values
        tenant_id = await self._extract(self.tenant_extractor, request)
        user_id = await self._extract(self.user_extractor, request)
        organization_id = await self._extract(self.organization_extractor, request)
        roles_result = await self._extract(self.roles_extractor, request)
        roles: list[str] = roles_result if roles_result else []

        # Extract custom values
        custom: dict[str, Any] = {}
        for key, extractor in self.custom_extractors.items():
            custom[key] = await self._extract(extractor, request)

        # Set the policy context
        set_policy_context(
            tenant_id=tenant_id,
            user_id=user_id,
            organization_id=organization_id,
            roles=roles,
            **custom,
        )

        try:
            await self.app(scope, receive, send)
        finally:
            clear_policy_context()

    async def _extract(
        self,
        extractor: Callable[[Any], Any] | None,
        request: Any,
    ) -> Any:
        """Extract a value using an extractor function.

        Handles both sync and async extractors.
        """
        if extractor is None:
            return None

        try:
            result = extractor(request)
            if inspect.isawaitable(result):
                return await result
            return result
        except (AttributeError, KeyError, TypeError, ValueError):
            # AttributeError: missing attribute on request object
            # KeyError: missing key in headers/dict
            # TypeError: invalid operation on value
            # ValueError: invalid value conversion
            return None


class _ScopeWrapper:
    """Wrapper around ASGI scope to provide request-like interface.

    Provides basic access to headers, path, query_string, etc.
    More advanced features require the actual Request object.
    """

    def __init__(self, scope: Scope) -> None:
        self._scope = scope
        self._headers: dict[str, str] | None = None

    @property
    def headers(self) -> dict[str, str]:
        """Get request headers as a dict."""
        if self._headers is None:
            self._headers = {}
            for key, value in self._scope.get("headers", []):
                self._headers[key.decode("latin-1").lower()] = value.decode("latin-1")
        return self._headers

    @property
    def path(self) -> str:
        """Get the request path."""
        return self._scope.get("path", "/")

    @property
    def query_string(self) -> bytes:
        """Get the raw query string."""
        return self._scope.get("query_string", b"")

    @property
    def method(self) -> str:
        """Get the request method."""
        return self._scope.get("method", "GET")

    @property
    def scope(self) -> Scope:
        """Get the raw ASGI scope."""
        return self._scope

    @property
    def state(self) -> Any:
        """Get the request state object.

        Returns the state object from the ASGI scope, which can be used
        to store and retrieve request-scoped data (e.g., user_id, roles).
        Returns an empty SimpleNamespace if no state is set, allowing
        safe attribute access via getattr(req.state, 'attr', default).
        """
        return self._scope.get("state") or types.SimpleNamespace()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the scope."""
        return self._scope.get(key, default)


def create_header_extractor(header_name: str) -> Callable[[Any], str | None]:
    """Create an extractor that gets a value from a request header.

    Args:
        header_name: The header name (case-insensitive).

    Returns:
        Extractor function.

    Example:
        tenant_extractor = create_header_extractor("X-Tenant-ID")
    """
    header_key = header_name.lower()

    def extractor(request: Any) -> str | None:
        if hasattr(request, "headers"):
            headers = request.headers
            if isinstance(headers, dict):
                return headers.get(header_key)
            elif hasattr(headers, "get"):
                return headers.get(header_key)
        return None

    return extractor


def create_state_extractor(state_key: str) -> Callable[[Any], Any]:
    """Create an extractor that gets a value from request.state.

    Args:
        state_key: The state attribute name.

    Returns:
        Extractor function.

    Example:
        user_extractor = create_state_extractor("user_id")
    """

    def extractor(request: Any) -> Any:
        if hasattr(request, "state"):
            return getattr(request.state, state_key, None)
        return None

    return extractor
