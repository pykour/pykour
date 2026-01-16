"""Tests for the dependency injection system."""

import pytest

from pykour.di import Depends, Scope, ServiceContainer, ServiceNotFoundError


class TestServiceContainer:
    """Tests for ServiceContainer."""

    def test_register_and_resolve(self) -> None:
        """Should register and resolve a simple service."""
        container = ServiceContainer()

        class UserService:
            def get_user(self) -> str:
                return "user"

        container.register(UserService)
        service = container.resolve(UserService)

        assert isinstance(service, UserService)
        assert service.get_user() == "user"

    def test_register_with_implementation(self) -> None:
        """Should register interface with implementation."""
        container = ServiceContainer()

        class IUserService:
            def get_user(self) -> str:
                raise NotImplementedError

        class UserServiceImpl(IUserService):
            def get_user(self) -> str:
                return "impl_user"

        container.register(IUserService, UserServiceImpl)
        service = container.resolve(IUserService)

        assert isinstance(service, UserServiceImpl)
        assert service.get_user() == "impl_user"

    def test_singleton_scope(self) -> None:
        """Should return same instance for singleton scope."""
        container = ServiceContainer()

        class ConfigService:
            pass

        container.register(ConfigService, scope=Scope.SINGLETON)

        service1 = container.resolve(ConfigService)
        service2 = container.resolve(ConfigService)

        assert service1 is service2

    def test_transient_scope(self) -> None:
        """Should return new instance for transient scope."""
        container = ServiceContainer()

        class RequestService:
            pass

        container.register(RequestService, scope=Scope.TRANSIENT)

        service1 = container.resolve(RequestService)
        service2 = container.resolve(RequestService)

        assert service1 is not service2

    def test_register_factory(self) -> None:
        """Should use factory function to create instances."""
        container = ServiceContainer()
        call_count = 0

        class DatabaseConnection:
            def __init__(self, url: str):
                self.url = url

        def create_connection() -> DatabaseConnection:
            nonlocal call_count
            call_count += 1
            return DatabaseConnection("postgresql://localhost/db")

        container.register_factory(DatabaseConnection, create_connection)

        service = container.resolve(DatabaseConnection)

        assert isinstance(service, DatabaseConnection)
        assert service.url == "postgresql://localhost/db"
        assert call_count == 1

    def test_register_factory_singleton(self) -> None:
        """Factory with singleton scope should only be called once."""
        container = ServiceContainer()
        call_count = 0

        class Config:
            def __init__(self):
                pass

        def create_config() -> Config:
            nonlocal call_count
            call_count += 1
            return Config()

        container.register_factory(Config, create_config, scope=Scope.SINGLETON)

        service1 = container.resolve(Config)
        service2 = container.resolve(Config)

        assert service1 is service2
        assert call_count == 1

    def test_register_instance(self) -> None:
        """Should use pre-created instance."""
        container = ServiceContainer()

        class Settings:
            def __init__(self, debug: bool):
                self.debug = debug

        settings = Settings(debug=True)
        container.register_instance(Settings, settings)

        service = container.resolve(Settings)

        assert service is settings
        assert service.debug is True

    def test_is_registered(self) -> None:
        """Should check if type is registered."""
        container = ServiceContainer()

        class ServiceA:
            pass

        class ServiceB:
            pass

        container.register(ServiceA)

        assert container.is_registered(ServiceA) is True
        assert container.is_registered(ServiceB) is False

    def test_resolve_not_found(self) -> None:
        """Should raise ServiceNotFoundError for unregistered type."""
        container = ServiceContainer()

        class UnknownService:
            pass

        with pytest.raises(ServiceNotFoundError) as exc_info:
            container.resolve(UnknownService)

        assert exc_info.value.service_type is UnknownService

    def test_resolve_or_none_found(self) -> None:
        """Should return instance when found."""
        container = ServiceContainer()

        class ServiceA:
            pass

        container.register(ServiceA)
        service = container.resolve_or_none(ServiceA)

        assert isinstance(service, ServiceA)

    def test_resolve_or_none_not_found(self) -> None:
        """Should return None when not found."""
        container = ServiceContainer()

        class UnknownService:
            pass

        service = container.resolve_or_none(UnknownService)

        assert service is None

    def test_clear(self) -> None:
        """Should clear all registrations."""
        container = ServiceContainer()

        class ServiceA:
            pass

        container.register(ServiceA)
        container.clear()

        assert container.is_registered(ServiceA) is False

    def test_clear_singletons(self) -> None:
        """Should clear singleton instances but keep registrations."""
        container = ServiceContainer()

        class ConfigService:
            pass

        container.register(ConfigService, scope=Scope.SINGLETON)

        service1 = container.resolve(ConfigService)
        container.clear_singletons()
        service2 = container.resolve(ConfigService)

        assert service1 is not service2
        assert container.is_registered(ConfigService) is True


class TestDependencyResolution:
    """Tests for automatic dependency resolution."""

    def test_resolve_with_dependencies(self) -> None:
        """Should automatically resolve constructor dependencies."""
        container = ServiceContainer()

        class Repository:
            def fetch(self) -> str:
                return "data"

        class Service:
            def __init__(self, repo: Repository):
                self.repo = repo

            def get_data(self) -> str:
                return self.repo.fetch()

        container.register(Repository)
        container.register(Service)

        service = container.resolve(Service)

        assert isinstance(service, Service)
        assert isinstance(service.repo, Repository)
        assert service.get_data() == "data"

    def test_resolve_nested_dependencies(self) -> None:
        """Should resolve nested dependencies."""
        container = ServiceContainer()

        class Database:
            def query(self) -> str:
                return "db_result"

        class Repository:
            def __init__(self, db: Database):
                self.db = db

            def fetch(self) -> str:
                return self.db.query()

        class Service:
            def __init__(self, repo: Repository):
                self.repo = repo

            def get_data(self) -> str:
                return self.repo.fetch()

        container.register(Database)
        container.register(Repository)
        container.register(Service)

        service = container.resolve(Service)

        assert service.get_data() == "db_result"

    def test_resolve_with_default_values(self) -> None:
        """Should use default values for unregistered dependencies."""
        container = ServiceContainer()

        class Service:
            def __init__(self, name: str = "default"):
                self.name = name

        container.register(Service)
        service = container.resolve(Service)

        assert service.name == "default"


class TestDepends:
    """Tests for Depends marker class."""

    def test_depends_no_args(self) -> None:
        """Should create Depends with no arguments."""
        dep = Depends()
        assert dep.dependency is None

    def test_depends_with_type(self) -> None:
        """Should create Depends with explicit type."""

        class UserService:
            pass

        dep = Depends(UserService)
        assert dep.dependency is UserService

    def test_depends_with_callable(self) -> None:
        """Should create Depends with factory callable."""

        def get_service() -> str:
            return "service"

        dep = Depends(get_service)
        assert dep.dependency is get_service


class TestIntegration:
    """Integration tests for DI with Pykour application."""

    def test_service_container_property(self) -> None:
        """Pykour should have a services property."""
        from pykour import Pykour

        app = Pykour()

        assert hasattr(app, "services")
        assert isinstance(app.services, ServiceContainer)

    def test_service_registration(self) -> None:
        """Should be able to register services on Pykour app."""
        from pykour import Pykour

        app = Pykour()

        class MyService:
            def do_something(self) -> str:
                return "done"

        app.services.register(MyService)

        assert app.services.is_registered(MyService)
        service = app.services.resolve(MyService)
        assert service.do_something() == "done"

    def test_singleton_service_via_app(self) -> None:
        """Singleton services should be shared."""
        from pykour import Pykour

        app = Pykour()

        class Counter:
            def __init__(self):
                self.count = 0

            def increment(self) -> int:
                self.count += 1
                return self.count

        app.services.register(Counter, scope=Scope.SINGLETON)

        counter1 = app.services.resolve(Counter)
        counter2 = app.services.resolve(Counter)

        assert counter1 is counter2
        assert counter1.increment() == 1
        assert counter2.increment() == 2

    def test_transient_service_via_app(self) -> None:
        """Transient services should create new instances."""
        from pykour import Pykour

        app = Pykour()

        class Request:
            pass

        app.services.register(Request, scope=Scope.TRANSIENT)

        request1 = app.services.resolve(Request)
        request2 = app.services.resolve(Request)

        assert request1 is not request2

    def test_factory_registration_via_app(self) -> None:
        """Should be able to register factories via app."""
        from pykour import Pykour

        app = Pykour()

        class Config:
            def __init__(self, debug: bool):
                self.debug = debug

        app.services.register_factory(Config, lambda: Config(debug=True))

        config = app.services.resolve(Config)
        assert config.debug is True

    def test_instance_registration_via_app(self) -> None:
        """Should be able to register instances via app."""
        from pykour import Pykour

        app = Pykour()

        class Settings:
            def __init__(self, env: str):
                self.env = env

        settings = Settings(env="production")
        app.services.register_instance(Settings, settings)

        resolved = app.services.resolve(Settings)
        assert resolved is settings
        assert resolved.env == "production"
