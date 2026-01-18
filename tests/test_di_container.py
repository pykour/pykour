"""Tests for dependency injection container."""

from __future__ import annotations

import pytest

from pykour.di.container import (
    Depends,
    Scope,
    ServiceContainer,
    ServiceNotFoundException,
    ServiceNotFoundError,
    ServiceRegistration,
)


# Module-level classes for DI tests (get_type_hints requires module-level classes)
class _DITestDependency:
    """Test dependency class for DI injection tests."""

    pass


class _DITestService:
    """Test service with dependency injection."""

    def __init__(self, dep: _DITestDependency) -> None:
        self.dep = dep


class _DITestServiceWithDepends:
    """Test service using Depends marker."""

    def __init__(self, dep: _DITestDependency = Depends()) -> None:  # type: ignore[assignment]
        self.dep = dep


class TestScope:
    """Tests for Scope enum."""

    def test_scope_values(self) -> None:
        """Scope has SINGLETON and TRANSIENT values."""
        assert Scope.SINGLETON is not None
        assert Scope.TRANSIENT is not None
        assert Scope.SINGLETON != Scope.TRANSIENT


class TestServiceRegistration:
    """Tests for ServiceRegistration dataclass."""

    def test_default_values(self) -> None:
        """ServiceRegistration has correct default values."""
        reg = ServiceRegistration(interface=str)
        assert reg.interface is str
        assert reg.implementation is None
        assert reg.factory is None
        assert reg.instance is None
        assert reg.scope == Scope.TRANSIENT

    def test_is_factory(self) -> None:
        """is_factory returns True when factory is set."""
        reg = ServiceRegistration(interface=str, factory=lambda: "test")
        assert reg.is_factory() is True

        reg_no_factory = ServiceRegistration(interface=str)
        assert reg_no_factory.is_factory() is False

    def test_is_instance(self) -> None:
        """is_instance returns True when instance is set."""
        reg = ServiceRegistration(interface=str, instance="test")
        assert reg.is_instance() is True

        reg_no_instance = ServiceRegistration(interface=str)
        assert reg_no_instance.is_instance() is False


class TestServiceNotFoundException:
    """Tests for ServiceNotFoundException."""

    def test_exception_message(self) -> None:
        """Exception includes service type name in message."""
        exc = ServiceNotFoundException(int)
        assert exc.service_type is int
        assert "int" in str(exc)

    def test_backward_compatibility_alias(self) -> None:
        """ServiceNotFoundError is an alias for ServiceNotFoundException."""
        assert ServiceNotFoundError is ServiceNotFoundException


class TestDepends:
    """Tests for Depends marker."""

    def test_depends_without_explicit_dependency(self) -> None:
        """Depends() without argument uses type hint."""
        dep = Depends()
        assert dep.dependency is None

    def test_depends_with_explicit_type(self) -> None:
        """Depends(Type) stores the explicit type."""
        dep = Depends(str)
        assert dep.dependency is str

    def test_depends_with_factory(self) -> None:
        """Depends(factory) stores the factory function."""

        def my_factory() -> str:
            return "test"

        dep = Depends(my_factory)
        assert dep.dependency is my_factory


class TestServiceContainerBasics:
    """Basic tests for ServiceContainer."""

    def test_empty_container(self) -> None:
        """New container has no registrations."""
        container = ServiceContainer()
        assert container.is_registered(str) is False

    def test_register_self(self) -> None:
        """Can register a class for itself."""

        class MyService:
            pass

        container = ServiceContainer()
        container.register(MyService)
        assert container.is_registered(MyService) is True

    def test_register_with_implementation(self) -> None:
        """Can register interface with implementation."""

        class IService:
            pass

        class ServiceImpl(IService):
            pass

        container = ServiceContainer()
        container.register(IService, ServiceImpl)
        assert container.is_registered(IService) is True

    def test_register_factory(self) -> None:
        """Can register a factory function."""
        container = ServiceContainer()
        container.register_factory(str, lambda: "hello")
        assert container.is_registered(str) is True

    def test_register_instance(self) -> None:
        """Can register a pre-created instance."""
        container = ServiceContainer()
        instance = "my_instance"
        container.register_instance(str, instance)
        assert container.is_registered(str) is True


class TestServiceContainerResolve:
    """Tests for ServiceContainer.resolve()."""

    def test_resolve_simple_class(self) -> None:
        """Can resolve a simple class."""

        class MyService:
            pass

        container = ServiceContainer()
        container.register(MyService)
        instance = container.resolve(MyService)
        assert isinstance(instance, MyService)

    def test_resolve_transient_creates_new_instances(self) -> None:
        """Transient scope creates new instance each time."""

        class MyService:
            pass

        container = ServiceContainer()
        container.register(MyService, scope=Scope.TRANSIENT)
        instance1 = container.resolve(MyService)
        instance2 = container.resolve(MyService)
        assert instance1 is not instance2

    def test_resolve_singleton_returns_same_instance(self) -> None:
        """Singleton scope returns same instance."""

        class MyService:
            pass

        container = ServiceContainer()
        container.register(MyService, scope=Scope.SINGLETON)
        instance1 = container.resolve(MyService)
        instance2 = container.resolve(MyService)
        assert instance1 is instance2

    def test_resolve_factory(self) -> None:
        """Can resolve factory registration."""
        container = ServiceContainer()
        container.register_factory(str, lambda: "hello")
        result = container.resolve(str)
        assert result == "hello"

    def test_resolve_instance(self) -> None:
        """Can resolve instance registration."""
        container = ServiceContainer()
        instance = {"key": "value"}
        container.register_instance(dict, instance)
        result = container.resolve(dict)
        assert result is instance

    def test_resolve_not_registered_raises(self) -> None:
        """Resolving unregistered type raises ServiceNotFoundException."""
        container = ServiceContainer()
        with pytest.raises(ServiceNotFoundException) as exc_info:
            container.resolve(int)
        assert exc_info.value.service_type is int

    def test_resolve_or_none_returns_none_for_unregistered(self) -> None:
        """resolve_or_none returns None for unregistered types."""
        container = ServiceContainer()
        result = container.resolve_or_none(int)
        assert result is None

    def test_resolve_or_none_returns_instance_for_registered(self) -> None:
        """resolve_or_none returns instance for registered types."""

        class MyService:
            pass

        container = ServiceContainer()
        container.register(MyService)
        result = container.resolve_or_none(MyService)
        assert isinstance(result, MyService)


class TestServiceContainerDependencyInjection:
    """Tests for dependency injection in ServiceContainer."""

    def test_resolve_with_dependencies(self) -> None:
        """Can resolve class with dependencies."""
        container = ServiceContainer()
        container.register(_DITestDependency)
        container.register(_DITestService)

        service = container.resolve(_DITestService)
        assert isinstance(service, _DITestService)
        assert isinstance(service.dep, _DITestDependency)

    def test_resolve_with_depends_marker(self) -> None:
        """Can resolve class with Depends marker."""
        container = ServiceContainer()
        container.register(_DITestDependency)
        container.register(_DITestServiceWithDepends)

        service = container.resolve(_DITestServiceWithDepends)
        assert isinstance(service.dep, _DITestDependency)

    def test_resolve_with_explicit_depends(self) -> None:
        """Depends with explicit type overrides type hint."""

        class Dependency1:
            pass

        class Dependency2:
            pass

        class MyService:
            def __init__(self, dep: Dependency1 = Depends(Dependency2)) -> None:  # type: ignore[assignment]
                self.dep = dep

        container = ServiceContainer()
        container.register(Dependency1)
        container.register(Dependency2)
        container.register(MyService)

        service = container.resolve(MyService)
        assert isinstance(service.dep, Dependency2)

    def test_resolve_with_factory_depends(self) -> None:
        """Depends with factory function calls the factory."""

        class MyService:
            def __init__(self, value: str = Depends(lambda: "factory_value")) -> None:  # type: ignore[assignment]
                self.value = value

        container = ServiceContainer()
        container.register(MyService)

        service = container.resolve(MyService)
        assert service.value == "factory_value"

    def test_resolve_missing_dependency_raises(self) -> None:
        """Resolving with missing dependency raises error."""

        class Dependency:
            pass

        class MyService:
            def __init__(self, dep: Dependency) -> None:
                self.dep = dep

        container = ServiceContainer()
        container.register(MyService)

        with pytest.raises(ValueError, match="Cannot resolve"):
            container.resolve(MyService)

    def test_resolve_missing_depends_dependency_raises(self) -> None:
        """Resolving with missing Depends dependency raises ServiceNotFoundException."""

        class Dependency:
            pass

        class MyService:
            def __init__(self, dep: Dependency = Depends()) -> None:  # type: ignore[assignment]
                self.dep = dep

        container = ServiceContainer()
        container.register(MyService)

        with pytest.raises(ServiceNotFoundException):
            container.resolve(MyService)

    def test_resolve_with_default_value(self) -> None:
        """Parameters with default values use defaults when not resolvable."""

        class MyService:
            def __init__(self, name: str = "default") -> None:
                self.name = name

        container = ServiceContainer()
        container.register(MyService)

        service = container.resolve(MyService)
        assert service.name == "default"


class TestServiceContainerClear:
    """Tests for ServiceContainer clear methods."""

    def test_clear_removes_all(self) -> None:
        """clear() removes all registrations and singletons."""

        class MyService:
            pass

        container = ServiceContainer()
        container.register(MyService, scope=Scope.SINGLETON)
        container.resolve(MyService)

        container.clear()

        assert container.is_registered(MyService) is False

    def test_clear_singletons_keeps_registrations(self) -> None:
        """clear_singletons() only clears cached instances."""

        class MyService:
            pass

        container = ServiceContainer()
        container.register(MyService, scope=Scope.SINGLETON)
        instance1 = container.resolve(MyService)

        container.clear_singletons()

        # Registration still exists
        assert container.is_registered(MyService) is True
        # But a new instance is created
        instance2 = container.resolve(MyService)
        assert instance1 is not instance2


class TestServiceContainerThreadSafety:
    """Tests for thread-safety of ServiceContainer."""

    def test_singleton_resolution_is_thread_safe(self) -> None:
        """Singleton resolution is thread-safe with concurrent access."""
        import threading

        class SlowService:
            def __init__(self) -> None:
                import time

                time.sleep(0.01)  # Simulate slow initialization

        container = ServiceContainer()
        container.register(SlowService, scope=Scope.SINGLETON)

        instances: list[SlowService] = []
        errors: list[Exception] = []

        def resolve_service() -> None:
            try:
                instance = container.resolve(SlowService)
                instances.append(instance)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=resolve_service) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(instances) == 10
        # All instances should be the same singleton
        assert all(inst is instances[0] for inst in instances)
