"""Dependency injection container implementation."""

from __future__ import annotations

import asyncio
import inspect
import threading
from contextvars import ContextVar, Token
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Awaitable, Callable, TypeVar, cast, get_type_hints

T = TypeVar("T")


class Scope(Enum):
    """Dependency scope types.

    SINGLETON: One instance shared across all requests.
    TRANSIENT: New instance created for each resolution.
    REQUEST: One instance per request (request-scoped singleton).
    """

    SINGLETON = auto()
    TRANSIENT = auto()
    REQUEST = auto()


class ServiceNotFoundException(Exception):
    """Exception raised when a requested service is not registered."""

    def __init__(self, service_type: type | str) -> None:
        self.service_type = service_type
        type_name = (
            service_type if isinstance(service_type, str) else service_type.__name__
        )
        super().__init__(f"Service not found: {type_name}")


class CircularDependencyError(Exception):
    """Exception raised when a circular dependency is detected.

    This occurs when service A depends on service B, which depends on
    service A (directly or indirectly).

    Example:
        class ServiceA:
            def __init__(self, b: ServiceB = Depends()): ...

        class ServiceB:
            def __init__(self, a: ServiceA = Depends()): ...

        # Resolving ServiceA will raise CircularDependencyError
    """

    def __init__(self, dependency_chain: list[str]) -> None:
        """Initialize with the dependency chain that caused the cycle.

        Args:
            dependency_chain: List of type names showing the cycle.
        """
        self.dependency_chain = dependency_chain
        chain_str = " -> ".join(dependency_chain)
        super().__init__(f"Circular dependency detected: {chain_str}")


# Backward compatibility alias
ServiceNotFoundError = ServiceNotFoundException


@dataclass
class ServiceRegistration:
    """Holds registration info for a service."""

    interface: type
    implementation: type | None = None
    factory: Callable[..., Any] | None = None
    instance: Any = None
    scope: Scope = Scope.TRANSIENT

    def is_factory(self) -> bool:
        """Check if this is a factory registration."""
        return self.factory is not None

    def is_instance(self) -> bool:
        """Check if this is an instance registration."""
        return self.instance is not None


class Depends:
    """Dependency injection marker.

    Use this as a default value for handler parameters to request
    dependency injection.

    Example:
        async def handler(user_service: UserService = Depends()) -> JSONResponse:
            ...

        # With explicit type
        async def handler(db: Database = Depends(Database)) -> JSONResponse:
            ...
    """

    def __init__(self, dependency: type | Callable[..., Any] | None = None) -> None:
        """Initialize Depends marker.

        Args:
            dependency: Optional explicit dependency type or factory.
                       If None, the parameter's type annotation is used.
        """
        self._dependency = dependency

    @property
    def dependency(self) -> type | Callable[..., Any] | None:
        """Get the explicit dependency type/factory."""
        return self._dependency


# ContextVar for request-scoped instances (async-safe, one dict per request)
_request_scope_instances: ContextVar[dict[type, Any] | None] = ContextVar(
    "_request_scope_instances", default=None
)


class RequestScope:
    """Context manager for request-scoped dependency injection.

    When active, services registered with ``Scope.REQUEST`` are created once
    per request and shared within that request.  Concurrent requests are fully
    isolated because each asyncio Task (i.e. each incoming HTTP request) gets
    its own copy of the ContextVar context.

    Example:
        container = ServiceContainer()
        container.register(MyService, scope=Scope.REQUEST)

        async with RequestScope():
            svc1 = await container.aresolve(MyService)
            svc2 = await container.aresolve(MyService)
            assert svc1 is svc2  # same instance within the request
    """

    def __init__(self) -> None:
        self._token: Token[dict[type, Any] | None] | None = None

    def __enter__(self) -> "RequestScope":
        self._token = _request_scope_instances.set({})
        return self

    def __exit__(self, *args: object) -> None:
        if self._token is not None:
            _request_scope_instances.reset(self._token)

    async def __aenter__(self) -> "RequestScope":
        return self.__enter__()

    async def __aexit__(self, *args: object) -> None:
        self.__exit__(*args)


class ServiceContainer:
    """Dependency injection container.

    Manages service registrations and resolves dependencies.

    Example:
        container = ServiceContainer()

        # Register a concrete class
        container.register(UserService)

        # Register with implementation
        container.register(IUserService, UserServiceImpl)

        # Register singleton
        container.register(ConfigService, scope=Scope.SINGLETON)

        # Register factory
        container.register_factory(Database, lambda: create_database())

        # Register async factory
        container.register_factory(Database, create_database_async, scope=Scope.SINGLETON)

        # Register instance
        container.register_instance(Config, config_obj)

        # Resolve (sync)
        service = container.resolve(UserService)

        # Resolve (async, supports async factories)
        service = await container.aresolve(UserService)
    """

    def __init__(self) -> None:
        """Initialize empty container."""
        self._registrations: dict[type, ServiceRegistration] = {}
        self._singletons: dict[type, Any] = {}
        self._singleton_lock = threading.Lock()
        self._async_singleton_lock: asyncio.Lock | None = None

    def register(
        self,
        interface: type[T],
        implementation: type[T] | None = None,
        *,
        scope: Scope = Scope.TRANSIENT,
    ) -> None:
        """Register a service type.

        Args:
            interface: The type to register (interface or concrete class).
            implementation: Optional implementation type. If None, interface
                           is used as both interface and implementation.
            scope: Service scope (SINGLETON, TRANSIENT, or REQUEST).

        Example:
            # Self-registration
            container.register(UserService)

            # Interface to implementation
            container.register(IUserService, UserServiceImpl)

            # Singleton
            container.register(ConfigService, scope=Scope.SINGLETON)

            # Request-scoped
            container.register(RequestContext, scope=Scope.REQUEST)
        """
        impl = implementation or interface
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            implementation=impl,
            scope=scope,
        )

    def register_factory(
        self,
        interface: type[T],
        factory: Callable[..., T] | Callable[..., Awaitable[T]],
        *,
        scope: Scope = Scope.TRANSIENT,
    ) -> None:
        """Register a factory function for creating service instances.

        Both synchronous and asynchronous factory functions are accepted.
        Use ``aresolve()`` to resolve services with async factories.

        Args:
            interface: The type to register.
            factory: Callable (sync or async) that creates instances.
            scope: Service scope.

        Example:
            container.register_factory(
                Database,
                lambda: Database.connect("postgresql://..."),
                scope=Scope.SINGLETON,
            )

            # Async factory
            async def create_db() -> Database:
                return await Database.connect_async("postgresql://...")

            container.register_factory(Database, create_db, scope=Scope.SINGLETON)
        """
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            factory=factory,
            scope=scope,
        )

    def register_instance(self, interface: type[T], instance: T) -> None:
        """Register a pre-created instance.

        The instance is always treated as a singleton.

        Args:
            interface: The type to register.
            instance: The instance to use.

        Example:
            config = Config(debug=True)
            container.register_instance(Config, config)
        """
        self._registrations[interface] = ServiceRegistration(
            interface=interface,
            instance=instance,
            scope=Scope.SINGLETON,
        )
        self._singletons[interface] = instance

    def is_registered(self, interface: type) -> bool:
        """Check if a type is registered.

        Args:
            interface: Type to check.

        Returns:
            True if the type is registered.
        """
        return interface in self._registrations

    def resolve(self, interface: type[T]) -> T:
        """Resolve a dependency (synchronous).

        This method is thread-safe for singleton resolution.
        For async factories, use ``aresolve()`` instead.

        Args:
            interface: Type to resolve.

        Returns:
            Instance of the requested type.

        Raises:
            ServiceNotFoundError: If the type is not registered.
            RuntimeError: If a REQUEST-scoped service is resolved outside a
                          RequestScope context manager.
        """
        if interface not in self._registrations:
            raise ServiceNotFoundError(interface)

        registration = self._registrations[interface]

        # Return existing singleton (fast path without lock)
        if registration.scope == Scope.SINGLETON and interface in self._singletons:
            return self._singletons[interface]

        # For REQUEST scope, look up in the current request's instance cache
        if registration.scope == Scope.REQUEST:
            request_cache = _request_scope_instances.get()
            if request_cache is None:
                raise RuntimeError(
                    "REQUEST scope cannot be resolved outside of a request context. "
                    "Ensure RequestScope context manager is active."
                )
            if interface in request_cache:
                return request_cache[interface]
            instance = self._create_instance(registration)
            request_cache[interface] = instance
            return instance

        # For transient scope, just create and return
        if registration.scope == Scope.TRANSIENT:
            return self._create_instance(registration)

        # For singleton scope, use lock to ensure thread-safety
        with self._singleton_lock:
            # Double-check after acquiring lock
            if interface in self._singletons:
                return self._singletons[interface]

            # Create instance and cache
            instance = self._create_instance(registration)
            self._singletons[interface] = instance
            return instance

    async def aresolve(self, interface: type[T]) -> T:
        """Resolve a dependency (asynchronous).

        Supports async factory functions.  Falls back gracefully to sync
        construction when no async factory is involved.

        Args:
            interface: Type to resolve.

        Returns:
            Instance of the requested type.

        Raises:
            ServiceNotFoundError: If the type is not registered.
            RuntimeError: If a REQUEST-scoped service is resolved outside a
                          RequestScope context manager.
        """
        if interface not in self._registrations:
            raise ServiceNotFoundError(interface)

        registration = self._registrations[interface]

        # Return existing singleton (fast path)
        if registration.scope == Scope.SINGLETON and interface in self._singletons:
            return self._singletons[interface]

        # For REQUEST scope, look up in the current request's instance cache
        if registration.scope == Scope.REQUEST:
            request_cache = _request_scope_instances.get()
            if request_cache is None:
                raise RuntimeError(
                    "REQUEST scope cannot be resolved outside of a request context. "
                    "Ensure RequestScope context manager is active."
                )
            if interface in request_cache:
                return request_cache[interface]
            instance = await self._create_instance_async(registration)
            request_cache[interface] = instance
            return instance

        # For transient scope, just create and return
        if registration.scope == Scope.TRANSIENT:
            return await self._create_instance_async(registration)

        # For singleton scope, use async lock to ensure safety in event loop
        if self._async_singleton_lock is None:
            self._async_singleton_lock = asyncio.Lock()

        async with self._async_singleton_lock:
            # Double-check after acquiring lock
            if interface in self._singletons:
                return self._singletons[interface]

            instance = await self._create_instance_async(registration)
            self._singletons[interface] = instance
            return instance

    def resolve_or_none(self, interface: type[T]) -> T | None:
        """Resolve a dependency, returning None if not found.

        Args:
            interface: Type to resolve.

        Returns:
            Instance of the requested type, or None if not registered.
        """
        try:
            return self.resolve(interface)
        except ServiceNotFoundError:
            return None

    def _create_instance(
        self,
        registration: ServiceRegistration,
        _resolving_chain: list[str] | None = None,
    ) -> Any:
        """Create an instance for a registration.

        Args:
            registration: Service registration info.
            _resolving_chain: Internal parameter for circular dependency detection.

        Returns:
            Created instance.
        """
        # Pre-registered instance
        if registration.is_instance():
            return registration.instance

        # Factory function
        if registration.is_factory():
            assert registration.factory is not None
            return self._call_with_dependencies(
                registration.factory, _resolving_chain=_resolving_chain
            )

        # Class instantiation
        if registration.implementation:
            return self._call_with_dependencies(
                registration.implementation, _resolving_chain=_resolving_chain
            )

        raise RuntimeError(f"Invalid registration for {registration.interface}")

    async def _create_instance_async(
        self,
        registration: ServiceRegistration,
        _resolving_chain: list[str] | None = None,
    ) -> Any:
        """Create an instance for a registration, supporting async factories.

        Args:
            registration: Service registration info.
            _resolving_chain: Internal parameter for circular dependency detection.

        Returns:
            Created instance.
        """
        # Pre-registered instance
        if registration.is_instance():
            return registration.instance

        # Factory function (may be async)
        if registration.is_factory():
            assert registration.factory is not None
            return await self._call_with_dependencies_async(
                registration.factory, _resolving_chain=_resolving_chain
            )

        # Class instantiation (constructor may have async-factory dependencies)
        if registration.implementation:
            return await self._call_with_dependencies_async(
                registration.implementation, _resolving_chain=_resolving_chain
            )

        raise RuntimeError(f"Invalid registration for {registration.interface}")

    def _call_with_dependencies(
        self,
        callable_obj: Callable[..., T],
        *,
        _resolving_chain: list[str] | None = None,
    ) -> T:
        """Call a callable, resolving its dependencies.

        Handles Depends markers in parameter defaults for explicit
        dependency injection requests.

        Args:
            callable_obj: Function or class to call.
            _resolving_chain: Internal parameter for circular dependency detection.

        Returns:
            Result of calling the callable.

        Raises:
            ValueError: If a required parameter cannot be resolved.
            ServiceNotFoundError: If a Depends-marked dependency is not registered.
            CircularDependencyError: If a circular dependency is detected.
        """
        sig = inspect.signature(callable_obj)
        hints = self._get_type_hints(callable_obj)

        # Initialize the resolving chain for circular dependency detection
        if _resolving_chain is None:
            _resolving_chain = []

        # Note: Circular dependency check is done in _resolve_with_chain,
        # not here, to avoid false positives when the same callable is
        # used for multiple parameters.

        kwargs: dict[str, Any] = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = hints.get(param_name)
            default = param.default
            is_required = default is inspect.Parameter.empty

            # Check if parameter has a Depends marker
            if isinstance(default, Depends):
                # Use explicit dependency from Depends, or fall back to type hint
                dep_type = default.dependency
                if dep_type is None:
                    dep_type = param_type

                if dep_type is not None:
                    if callable(dep_type) and not isinstance(dep_type, type):
                        # It's a factory function, call it with dependencies
                        kwargs[param_name] = self._call_with_dependencies(
                            dep_type, _resolving_chain=_resolving_chain
                        )
                    elif self.is_registered(dep_type):
                        kwargs[param_name] = self._resolve_with_chain(
                            dep_type, _resolving_chain
                        )
                    else:
                        raise ServiceNotFoundError(dep_type)
                else:
                    raise ValueError(
                        f"Parameter '{param_name}' has Depends() but no type hint "
                        "and no explicit dependency specified"
                    )
                continue

            # No type hint - use default or raise error if required
            if param_type is None:
                if is_required:
                    callable_name = getattr(
                        callable_obj, "__name__", repr(callable_obj)
                    )
                    raise ValueError(
                        f"Cannot resolve required parameter '{param_name}' of "
                        f"'{callable_name}': no type hint and no default value"
                    )
                kwargs[param_name] = default
                continue

            # Try to resolve dependency by type
            if self.is_registered(param_type):
                kwargs[param_name] = self._resolve_with_chain(
                    param_type, _resolving_chain
                )
            elif not is_required:
                kwargs[param_name] = default
            else:
                callable_name = getattr(callable_obj, "__name__", repr(callable_obj))
                type_name = (
                    param_type if isinstance(param_type, str) else param_type.__name__
                )
                raise ValueError(
                    f"Cannot resolve required parameter '{param_name}' of "
                    f"'{callable_name}': type '{type_name}' is not "
                    "registered in the container"
                )

        return callable_obj(**kwargs)

    async def _call_with_dependencies_async(
        self,
        callable_obj: Callable[..., T],
        *,
        _resolving_chain: list[str] | None = None,
    ) -> T:
        """Call a callable (sync or async), resolving its dependencies asynchronously.

        Like ``_call_with_dependencies`` but supports async factory functions
        as both the callable itself and as dependencies of its parameters.

        Args:
            callable_obj: Sync or async function/class to call.
            _resolving_chain: Internal parameter for circular dependency detection.

        Returns:
            Result of calling the callable (awaited if coroutine).

        Raises:
            ValueError: If a required parameter cannot be resolved.
            ServiceNotFoundError: If a Depends-marked dependency is not registered.
            CircularDependencyError: If a circular dependency is detected.
        """
        sig = inspect.signature(callable_obj)
        hints = self._get_type_hints(callable_obj)

        if _resolving_chain is None:
            _resolving_chain = []

        kwargs: dict[str, Any] = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = hints.get(param_name)
            default = param.default
            is_required = default is inspect.Parameter.empty

            # Check if parameter has a Depends marker
            if isinstance(default, Depends):
                dep_type = default.dependency
                if dep_type is None:
                    dep_type = param_type

                if dep_type is not None:
                    if callable(dep_type) and not isinstance(dep_type, type):
                        kwargs[param_name] = await self._call_with_dependencies_async(
                            dep_type, _resolving_chain=_resolving_chain
                        )
                    elif self.is_registered(dep_type):
                        kwargs[param_name] = await self._aresolve_with_chain(
                            dep_type, _resolving_chain
                        )
                    else:
                        raise ServiceNotFoundError(dep_type)
                else:
                    raise ValueError(
                        f"Parameter '{param_name}' has Depends() but no type hint "
                        "and no explicit dependency specified"
                    )
                continue

            # No type hint
            if param_type is None:
                if is_required:
                    callable_name = getattr(
                        callable_obj, "__name__", repr(callable_obj)
                    )
                    raise ValueError(
                        f"Cannot resolve required parameter '{param_name}' of "
                        f"'{callable_name}': no type hint and no default value"
                    )
                kwargs[param_name] = default
                continue

            # Try to resolve dependency by type
            if self.is_registered(param_type):
                kwargs[param_name] = await self._aresolve_with_chain(
                    param_type, _resolving_chain
                )
            elif not is_required:
                kwargs[param_name] = default
            else:
                callable_name = getattr(callable_obj, "__name__", repr(callable_obj))
                type_name = (
                    param_type if isinstance(param_type, str) else param_type.__name__
                )
                raise ValueError(
                    f"Cannot resolve required parameter '{param_name}' of "
                    f"'{callable_name}': type '{type_name}' is not "
                    "registered in the container"
                )

        result = callable_obj(**kwargs)
        if inspect.isawaitable(result):
            return cast(T, await result)
        return result

    def _resolve_with_chain(self, interface: type[T], resolving_chain: list[str]) -> T:
        """Resolve a dependency with circular dependency tracking.

        Args:
            interface: Type to resolve.
            resolving_chain: Current chain of dependencies being resolved.

        Returns:
            Instance of the requested type.

        Raises:
            ServiceNotFoundError: If the type is not registered.
            CircularDependencyError: If a circular dependency is detected.
        """
        if interface not in self._registrations:
            raise ServiceNotFoundError(interface)

        registration = self._registrations[interface]
        type_name = interface.__name__

        # Check for circular dependency
        if type_name in resolving_chain:
            raise CircularDependencyError([*resolving_chain, type_name])

        # Return existing singleton (fast path without lock)
        if registration.scope == Scope.SINGLETON and interface in self._singletons:
            return self._singletons[interface]

        # For REQUEST scope, look up in the current request's instance cache
        if registration.scope == Scope.REQUEST:
            request_cache = _request_scope_instances.get()
            if request_cache is None:
                raise RuntimeError(
                    "REQUEST scope cannot be resolved outside of a request context. "
                    "Ensure RequestScope context manager is active."
                )
            if interface in request_cache:
                return request_cache[interface]
            instance = self._create_instance(
                registration, _resolving_chain=[*resolving_chain, type_name]
            )
            request_cache[interface] = instance
            return instance

        # For transient scope, just create and return
        if registration.scope == Scope.TRANSIENT:
            return self._create_instance(
                registration, _resolving_chain=[*resolving_chain, type_name]
            )

        # For singleton scope, use lock to ensure thread-safety
        with self._singleton_lock:
            # Double-check after acquiring lock
            if interface in self._singletons:
                return self._singletons[interface]

            # Create instance and cache
            instance = self._create_instance(
                registration, _resolving_chain=[*resolving_chain, type_name]
            )
            self._singletons[interface] = instance
            return instance

    async def _aresolve_with_chain(
        self, interface: type[T], resolving_chain: list[str]
    ) -> T:
        """Async resolve a dependency with circular dependency tracking.

        Args:
            interface: Type to resolve.
            resolving_chain: Current chain of dependencies being resolved.

        Returns:
            Instance of the requested type.

        Raises:
            ServiceNotFoundError: If the type is not registered.
            CircularDependencyError: If a circular dependency is detected.
        """
        if interface not in self._registrations:
            raise ServiceNotFoundError(interface)

        registration = self._registrations[interface]
        type_name = interface.__name__

        # Check for circular dependency
        if type_name in resolving_chain:
            raise CircularDependencyError([*resolving_chain, type_name])

        # Return existing singleton (fast path)
        if registration.scope == Scope.SINGLETON and interface in self._singletons:
            return self._singletons[interface]

        # For REQUEST scope
        if registration.scope == Scope.REQUEST:
            request_cache = _request_scope_instances.get()
            if request_cache is None:
                raise RuntimeError(
                    "REQUEST scope cannot be resolved outside of a request context. "
                    "Ensure RequestScope context manager is active."
                )
            if interface in request_cache:
                return request_cache[interface]
            instance = await self._create_instance_async(
                registration, _resolving_chain=[*resolving_chain, type_name]
            )
            request_cache[interface] = instance
            return instance

        # For transient scope
        if registration.scope == Scope.TRANSIENT:
            return await self._create_instance_async(
                registration, _resolving_chain=[*resolving_chain, type_name]
            )

        # For singleton scope
        if self._async_singleton_lock is None:
            self._async_singleton_lock = asyncio.Lock()

        async with self._async_singleton_lock:
            if interface in self._singletons:
                return self._singletons[interface]

            instance = await self._create_instance_async(
                registration, _resolving_chain=[*resolving_chain, type_name]
            )
            self._singletons[interface] = instance
            return instance

    def _get_type_hints(self, callable_obj: Callable[..., Any]) -> dict[str, Any]:
        """Get type hints for a callable.

        For classes, gets hints from __init__ method.

        Args:
            callable_obj: Function or class to get hints for.

        Returns:
            Dictionary of parameter name to type.
        """
        target = callable_obj
        if inspect.isclass(callable_obj):
            target = getattr(callable_obj, "__init__", callable_obj)

        try:
            return get_type_hints(target)
        except Exception:
            # Fallback to direct annotations
            return getattr(target, "__annotations__", {})

    def clear(self) -> None:
        """Clear all registrations and cached instances."""
        self._registrations.clear()
        self._singletons.clear()

    def clear_singletons(self) -> None:
        """Clear only cached singleton instances.

        Useful for testing to reset state between tests.
        """
        self._singletons.clear()
