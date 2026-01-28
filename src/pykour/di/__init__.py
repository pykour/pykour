"""Pykour Dependency Injection System.

This module provides a flexible dependency injection system that supports:
- Service registration (classes, factories, instances)
- Multiple scopes (singleton, transient)
- Type-based resolution
- Interface-to-implementation binding

Example:
    from pykour import Pykour
    from pykour.di import Depends, Scope

    # Define a service interface/class
    class UserService:
        async def get_user(self, user_id: int) -> dict:
            ...

    class UserServiceImpl(UserService):
        def __init__(self, db: Database):
            self.db = db

        async def get_user(self, user_id: int) -> dict:
            return await self.db.select("*").from_("users") \\
                .where(id=user_id).fetch_one()

    # Register services
    app = Pykour()
    app.services.register(UserService, UserServiceImpl)

    # Use in handlers
    async def get_user(
        user_id: int,
        user_service: UserService = Depends(),
    ) -> JSONResponse:
        user = await user_service.get_user(user_id)
        return JSONResponse(user)
"""

from pykour.di.container import (
    CircularDependencyError,
    Depends,
    Scope,
    ServiceContainer,
    # New exception name (preferred)
    ServiceNotFoundException,
    # Legacy alias (backward compatibility)
    ServiceNotFoundError,
    ServiceRegistration,
)

__all__ = [
    "CircularDependencyError",
    "Depends",
    "Scope",
    "ServiceContainer",
    "ServiceNotFoundException",  # New name
    "ServiceNotFoundError",  # Legacy alias
    "ServiceRegistration",
]
