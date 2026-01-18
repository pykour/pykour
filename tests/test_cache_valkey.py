"""Tests for Valkey cache storage backend."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pykour.cache.exceptions import CacheConnectionError
from pykour.cache.storage import CacheStorage


# Create mock valkey module before importing ValkeyStorage
mock_valkey_module = MagicMock()
mock_valkey_module.Valkey = MagicMock


@pytest.fixture(autouse=True)
def setup_valkey_mock() -> None:
    """Set up valkey mock for all tests."""
    # Ensure the mock module is available
    sys.modules["valkey"] = MagicMock()
    sys.modules["valkey.asyncio"] = mock_valkey_module


def create_valkey_storage_class() -> type:
    """Create ValkeyStorage class with mocked valkey dependency."""

    class ValkeyStorage(CacheStorage):
        """Valkey (Redis-compatible) cache storage backend (test version)."""

        def __init__(
            self,
            url: str = "valkey://localhost:6379",
            prefix: str = "pykour:",
            **options: Any,
        ) -> None:
            self._url = url
            self._prefix = prefix
            self._options = options
            self._client: Any = None

        def _make_key(self, key: str) -> str:
            return f"{self._prefix}{key}"

        async def connect(self) -> None:
            if self._client is not None:
                return
            try:
                self._client = mock_valkey_module.from_url(self._url, **self._options)
                await self._client.ping()
            except Exception as e:
                self._client = None
                raise CacheConnectionError(f"Failed to connect to Valkey: {e}") from e

        async def disconnect(self) -> None:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

        def _ensure_connected(self) -> Any:
            if self._client is None:
                raise CacheConnectionError(
                    "Valkey client not connected. Call connect() first."
                )
            return self._client

        async def get(self, key: str) -> bytes | None:
            client = self._ensure_connected()
            return await client.get(self._make_key(key))

        async def set(self, key: str, value: bytes, ttl: int | None = None) -> None:
            client = self._ensure_connected()
            full_key = self._make_key(key)
            if ttl is not None:
                await client.setex(full_key, ttl, value)
            else:
                await client.set(full_key, value)

        async def delete(self, key: str) -> bool:
            client = self._ensure_connected()
            result = await client.delete(self._make_key(key))
            return result > 0

        async def delete_pattern(self, pattern: str) -> int:
            client = self._ensure_connected()
            full_pattern = self._make_key(pattern)
            deleted = 0
            cursor = 0
            while True:
                cursor, keys = await client.scan(cursor, match=full_pattern, count=100)
                if keys:
                    deleted += await client.delete(*keys)
                if cursor == 0:
                    break
            return deleted

        async def exists(self, key: str) -> bool:
            client = self._ensure_connected()
            result = await client.exists(self._make_key(key))
            return result > 0

        async def clear(self) -> None:
            await self.delete_pattern("*")

    return ValkeyStorage


class TestValkeyStorage:
    """Tests for ValkeyStorage."""

    @pytest.fixture
    def mock_client(self) -> AsyncMock:
        """Create a mock Valkey client."""
        client = AsyncMock()
        client.ping = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock(return_value=True)
        client.setex = AsyncMock(return_value=True)
        client.delete = AsyncMock(return_value=1)
        client.exists = AsyncMock(return_value=1)
        client.scan = AsyncMock(return_value=(0, []))
        client.aclose = AsyncMock()
        return client

    @pytest.fixture
    def storage_class(self, mock_client: AsyncMock) -> type:
        """Get ValkeyStorage class with mocked client."""
        mock_valkey_module.from_url = MagicMock(return_value=mock_client)
        return create_valkey_storage_class()

    async def test_init_default_values(self, storage_class: type) -> None:
        """Test initialization with default values."""
        storage = storage_class()
        assert storage._url == "valkey://localhost:6379"
        assert storage._prefix == "pykour:"
        assert storage._client is None

    async def test_init_custom_values(self, storage_class: type) -> None:
        """Test initialization with custom values."""
        storage = storage_class(
            url="valkey://custom:6380",
            prefix="myapp:",
            decode_responses=False,
        )
        assert storage._url == "valkey://custom:6380"
        assert storage._prefix == "myapp:"
        assert storage._options == {"decode_responses": False}

    async def test_make_key(self, storage_class: type) -> None:
        """Test key prefix is added correctly."""
        storage = storage_class(prefix="test:")
        assert storage._make_key("foo") == "test:foo"
        assert storage._make_key("bar:baz") == "test:bar:baz"

    async def test_connect_success(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test successful connection."""
        storage = storage_class()
        await storage.connect()

        mock_valkey_module.from_url.assert_called_once_with("valkey://localhost:6379")
        mock_client.ping.assert_awaited_once()
        assert storage._client is not None

    async def test_connect_already_connected(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test that connect is idempotent when already connected."""
        storage = storage_class()
        await storage.connect()
        await storage.connect()  # Second call should be no-op

        # from_url should only be called once
        assert mock_valkey_module.from_url.call_count == 1

    async def test_connect_failure(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test connection failure raises CacheConnectionError."""
        mock_client.ping.side_effect = Exception("Connection refused")

        storage = storage_class()
        with pytest.raises(CacheConnectionError) as exc_info:
            await storage.connect()

        assert "Failed to connect to Valkey" in str(exc_info.value)
        assert storage._client is None

    async def test_disconnect(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test disconnect closes the client."""
        storage = storage_class()
        await storage.connect()
        await storage.disconnect()

        mock_client.aclose.assert_awaited_once()
        assert storage._client is None

    async def test_disconnect_when_not_connected(
        self,
        storage_class: type,
    ) -> None:
        """Test disconnect when not connected is a no-op."""
        storage = storage_class()
        await storage.disconnect()  # Should not raise

    async def test_ensure_connected_raises_when_not_connected(
        self,
        storage_class: type,
    ) -> None:
        """Test _ensure_connected raises when not connected."""
        storage = storage_class()
        with pytest.raises(CacheConnectionError) as exc_info:
            storage._ensure_connected()

        assert "not connected" in str(exc_info.value)

    async def test_get_success(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test getting a value."""
        mock_client.get.return_value = b"test_value"

        storage = storage_class(prefix="test:")
        await storage.connect()
        result = await storage.get("key1")

        mock_client.get.assert_awaited_once_with("test:key1")
        assert result == b"test_value"

    async def test_get_nonexistent_key(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test getting a nonexistent key returns None."""
        mock_client.get.return_value = None

        storage = storage_class()
        await storage.connect()
        result = await storage.get("nonexistent")

        assert result is None

    async def test_get_without_connection(self, storage_class: type) -> None:
        """Test get raises when not connected."""
        storage = storage_class()
        with pytest.raises(CacheConnectionError):
            await storage.get("key1")

    async def test_set_without_ttl(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test setting a value without TTL."""
        storage = storage_class(prefix="test:")
        await storage.connect()
        await storage.set("key1", b"value1")

        mock_client.set.assert_awaited_once_with("test:key1", b"value1")
        mock_client.setex.assert_not_awaited()

    async def test_set_with_ttl(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test setting a value with TTL."""
        storage = storage_class(prefix="test:")
        await storage.connect()
        await storage.set("key1", b"value1", ttl=300)

        mock_client.setex.assert_awaited_once_with("test:key1", 300, b"value1")
        mock_client.set.assert_not_awaited()

    async def test_set_without_connection(self, storage_class: type) -> None:
        """Test set raises when not connected."""
        storage = storage_class()
        with pytest.raises(CacheConnectionError):
            await storage.set("key1", b"value1")

    async def test_delete_existing_key(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test deleting an existing key returns True."""
        mock_client.delete.return_value = 1

        storage = storage_class(prefix="test:")
        await storage.connect()
        result = await storage.delete("key1")

        mock_client.delete.assert_awaited_once_with("test:key1")
        assert result is True

    async def test_delete_nonexistent_key(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test deleting a nonexistent key returns False."""
        mock_client.delete.return_value = 0

        storage = storage_class()
        await storage.connect()
        result = await storage.delete("nonexistent")

        assert result is False

    async def test_delete_without_connection(self, storage_class: type) -> None:
        """Test delete raises when not connected."""
        storage = storage_class()
        with pytest.raises(CacheConnectionError):
            await storage.delete("key1")

    async def test_delete_pattern_no_matches(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test delete_pattern with no matching keys."""
        mock_client.scan.return_value = (0, [])

        storage = storage_class(prefix="test:")
        await storage.connect()
        result = await storage.delete_pattern("user:*")

        mock_client.scan.assert_awaited_once_with(0, match="test:user:*", count=100)
        assert result == 0

    async def test_delete_pattern_with_matches(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test delete_pattern with matching keys."""
        mock_client.scan.return_value = (
            0,
            [b"test:user:1", b"test:user:2", b"test:user:3"],
        )
        mock_client.delete.return_value = 3

        storage = storage_class(prefix="test:")
        await storage.connect()
        result = await storage.delete_pattern("user:*")

        assert result == 3
        mock_client.delete.assert_awaited_once_with(
            b"test:user:1", b"test:user:2", b"test:user:3"
        )

    async def test_delete_pattern_multiple_scan_iterations(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test delete_pattern with multiple SCAN iterations."""
        mock_client.scan.side_effect = [
            (123, [b"test:user:1", b"test:user:2"]),
            (0, [b"test:user:3"]),
        ]
        mock_client.delete.side_effect = [2, 1]

        storage = storage_class(prefix="test:")
        await storage.connect()
        result = await storage.delete_pattern("user:*")

        assert result == 3
        assert mock_client.scan.await_count == 2

    async def test_delete_pattern_without_connection(self, storage_class: type) -> None:
        """Test delete_pattern raises when not connected."""
        storage = storage_class()
        with pytest.raises(CacheConnectionError):
            await storage.delete_pattern("user:*")

    async def test_exists_key_exists(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test exists returns True when key exists."""
        mock_client.exists.return_value = 1

        storage = storage_class(prefix="test:")
        await storage.connect()
        result = await storage.exists("key1")

        mock_client.exists.assert_awaited_once_with("test:key1")
        assert result is True

    async def test_exists_key_not_exists(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test exists returns False when key does not exist."""
        mock_client.exists.return_value = 0

        storage = storage_class()
        await storage.connect()
        result = await storage.exists("nonexistent")

        assert result is False

    async def test_exists_without_connection(self, storage_class: type) -> None:
        """Test exists raises when not connected."""
        storage = storage_class()
        with pytest.raises(CacheConnectionError):
            await storage.exists("key1")

    async def test_clear(
        self,
        storage_class: type,
        mock_client: AsyncMock,
    ) -> None:
        """Test clear deletes all keys with prefix."""
        mock_client.scan.return_value = (
            0,
            [b"pykour:key1", b"pykour:key2", b"pykour:key3"],
        )
        mock_client.delete.return_value = 3

        storage = storage_class()
        await storage.connect()
        await storage.clear()

        mock_client.scan.assert_awaited_once_with(0, match="pykour:*", count=100)

    async def test_clear_without_connection(self, storage_class: type) -> None:
        """Test clear raises when not connected."""
        storage = storage_class()
        with pytest.raises(CacheConnectionError):
            await storage.clear()


class TestValkeyStorageModuleImport:
    """Tests for ValkeyStorage module import behavior."""

    def test_import_error_message(self) -> None:
        """Test that ImportError message is helpful when valkey-py is not installed."""
        # Remove valkey from modules if it exists
        original_modules = {}
        for mod_name in list(sys.modules.keys()):
            if mod_name.startswith("valkey") or mod_name == "pykour.cache.valkey":
                original_modules[mod_name] = sys.modules.pop(mod_name)

        try:
            # Mock import to fail
            with patch.dict("sys.modules", {"valkey": None, "valkey.asyncio": None}):
                with pytest.raises(ImportError) as exc_info:
                    import importlib
                    import importlib.util

                    # Try to import the module fresh
                    spec = importlib.util.spec_from_file_location(
                        "pykour.cache.valkey",
                        "src/pykour/cache/valkey.py",
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                assert "valkey-py is required" in str(exc_info.value)
        finally:
            # Restore original modules
            sys.modules.update(original_modules)
