"""Tests for DI async factory support and REQUEST scope."""

from __future__ import annotations

import asyncio

import pytest

from pykour.di.container import (
    RequestScope,
    Scope,
    ServiceContainer,
    _request_scope_instances,
)


# ---------------------------------------------------------------------------
# Test service classes (must be module-level for get_type_hints)
# ---------------------------------------------------------------------------


class _AsyncSvc:
    """Simple service used in async factory tests."""

    def __init__(self, value: str) -> None:
        self.value = value


class _RequestScopedSvc:
    """Service for REQUEST scope tests."""

    pass


class _TransientSvc:
    """Service for TRANSIENT scope tests."""

    pass


class _SyncSvc:
    """Service for sync-factory-via-aresolve tests."""

    def __init__(self, value: str) -> None:
        self.value = value


# ---------------------------------------------------------------------------
# Test 1: async factory is awaited by aresolve()
# ---------------------------------------------------------------------------


async def test_async_factory_resolution() -> None:
    """aresolve() calls and awaits an async factory function."""
    call_count = 0

    async def async_factory() -> _AsyncSvc:
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0)  # simulate async I/O
        return _AsyncSvc("from_async")

    container = ServiceContainer()
    container.register_factory(_AsyncSvc, async_factory, scope=Scope.TRANSIENT)

    result = await container.aresolve(_AsyncSvc)

    assert isinstance(result, _AsyncSvc)
    assert result.value == "from_async"
    assert call_count == 1


# ---------------------------------------------------------------------------
# Test 2: async SINGLETON factory is called only once
# ---------------------------------------------------------------------------


async def test_async_factory_singleton() -> None:
    """Async SINGLETON factory is called exactly once across multiple aresolve() calls."""
    call_count = 0

    async def async_factory() -> _AsyncSvc:
        nonlocal call_count
        call_count += 1
        return _AsyncSvc("singleton")

    container = ServiceContainer()
    container.register_factory(_AsyncSvc, async_factory, scope=Scope.SINGLETON)

    svc1 = await container.aresolve(_AsyncSvc)
    svc2 = await container.aresolve(_AsyncSvc)

    assert svc1 is svc2
    assert call_count == 1


# ---------------------------------------------------------------------------
# Test 3: sync factory also works with aresolve() (backward compatibility)
# ---------------------------------------------------------------------------


async def test_sync_factory_with_aresolve() -> None:
    """aresolve() works with synchronous factory functions (backward compat)."""
    call_count = 0

    def sync_factory() -> _SyncSvc:
        nonlocal call_count
        call_count += 1
        return _SyncSvc("from_sync")

    container = ServiceContainer()
    container.register_factory(_SyncSvc, sync_factory, scope=Scope.TRANSIENT)

    result = await container.aresolve(_SyncSvc)

    assert isinstance(result, _SyncSvc)
    assert result.value == "from_sync"
    assert call_count == 1


# ---------------------------------------------------------------------------
# Test 4: REQUEST scope — same instance within a single RequestScope
# ---------------------------------------------------------------------------


async def test_request_scope_basic() -> None:
    """REQUEST-scoped service returns the same instance within a RequestScope."""
    container = ServiceContainer()
    container.register(_RequestScopedSvc, scope=Scope.REQUEST)

    async with RequestScope():
        svc1 = await container.aresolve(_RequestScopedSvc)
        svc2 = await container.aresolve(_RequestScopedSvc)

    assert svc1 is svc2


# ---------------------------------------------------------------------------
# Test 5: REQUEST scope isolation between concurrent tasks
# ---------------------------------------------------------------------------


async def test_request_scope_isolation() -> None:
    """Concurrent tasks each get their own REQUEST-scoped instance."""
    container = ServiceContainer()
    container.register(_RequestScopedSvc, scope=Scope.REQUEST)

    instances: dict[str, _RequestScopedSvc] = {}

    async def request_handler(name: str) -> None:
        async with RequestScope():
            instances[name] = await container.aresolve(_RequestScopedSvc)

    # create_task gives each task its own ContextVar copy
    await asyncio.gather(
        asyncio.create_task(request_handler("req1")),
        asyncio.create_task(request_handler("req2")),
    )

    assert "req1" in instances
    assert "req2" in instances
    assert instances["req1"] is not instances["req2"]


# ---------------------------------------------------------------------------
# Test 6: REQUEST scope — cache is cleared after RequestScope exits
# ---------------------------------------------------------------------------


async def test_request_scope_cleanup() -> None:
    """The REQUEST scope instance cache is cleared after the context manager exits."""
    container = ServiceContainer()
    container.register(_RequestScopedSvc, scope=Scope.REQUEST)

    async with RequestScope():
        svc_inside = await container.aresolve(_RequestScopedSvc)

    # After the scope exits the ContextVar is reset; a new scope creates fresh instances
    async with RequestScope():
        svc_next_request = await container.aresolve(_RequestScopedSvc)

    assert svc_inside is not svc_next_request


# ---------------------------------------------------------------------------
# Test 7: RuntimeError when REQUEST scope is resolved outside RequestScope
# ---------------------------------------------------------------------------


async def test_request_scope_outside_error() -> None:
    """Resolving a REQUEST-scoped service outside a RequestScope raises RuntimeError."""
    container = ServiceContainer()
    container.register(_RequestScopedSvc, scope=Scope.REQUEST)

    # Make sure no scope is active
    assert _request_scope_instances.get() is None

    with pytest.raises(RuntimeError, match="REQUEST scope cannot be resolved outside"):
        await container.aresolve(_RequestScopedSvc)


async def test_request_scope_outside_error_sync() -> None:
    """Sync resolve() also raises RuntimeError for REQUEST scope outside context."""
    container = ServiceContainer()
    container.register(_RequestScopedSvc, scope=Scope.REQUEST)

    assert _request_scope_instances.get() is None

    with pytest.raises(RuntimeError, match="REQUEST scope cannot be resolved outside"):
        container.resolve(_RequestScopedSvc)


# ---------------------------------------------------------------------------
# Test 8: TRANSIENT services are NOT cached within a RequestScope
# ---------------------------------------------------------------------------


async def test_transient_not_cached_in_request_scope() -> None:
    """TRANSIENT services always create a new instance, even inside a RequestScope."""
    container = ServiceContainer()
    container.register(_TransientSvc, scope=Scope.TRANSIENT)

    async with RequestScope():
        svc1 = await container.aresolve(_TransientSvc)
        svc2 = await container.aresolve(_TransientSvc)

    assert svc1 is not svc2
