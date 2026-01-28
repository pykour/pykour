"""Dependency injection container implementation."""

from __future__ import annotations

import inspect
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, TypeVar, get_type_hints

T = TypeVar("T")


class Scope(Enum):
    """Dependency scope types.

    SINGLETON: One instance shared across all requests.
    TRANSIENT: New instance created for each resolution.
    """

    SINGLETON = auto()
    TRANSIENT = auto()


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

        # Register instance
        container.register_instance(Config, config_obj)

        # Resolve
        service = container.resolve(UserService)
    """

    def __init__(self) -> None:
        """Initialize empty container."""
        self._registrations: dict[type, ServiceRegistration] = {}
        self._singletons: dict[type, Any] = {}
        self._singleton_lock = threading.Lock()

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
            scope: Service scope (SINGLETON or TRANSIENT).

        Example:
            # Self-registration
            container.register(UserService)

            # Interface to implementation
            container.register(IUserService, UserServiceImpl)

            # Singleton
            container.register(ConfigService, scope=Scope.SINGLETON)
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
        factory: Callable[..., T],
        *,
        scope: Scope = Scope.TRANSIENT,
    ) -> None:
        """Register a factory function for creating service instances.

        Args:
            interface: The type to register.
            factory: Callable that creates instances.
            scope: Service scope.

        Example:
            container.register_factory(
                Database,
                lambda: Database.connect("postgresql://..."),
                scope=Scope.SINGLETON,
            )
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
        """Resolve a dependency.

        This method is thread-safe for singleton resolution.

        Args:
            interface: Type to resolve.

        Returns:
            Instance of the requested type.

        Raises:
            ServiceNotFoundError: If the type is not registered.
        """
        if interface not in self._registrations:
            raise ServiceNotFoundError(interface)

        registration = self._registrations[interface]

        # Return existing singleton (fast path without lock)
        if registration.scope == Scope.SINGLETON and interface in self._singletons:
            return self._singletons[interface]

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
