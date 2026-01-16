"""Tests for cache decorators."""

from pykour.cache.decorators import (
    CACHE_EVICT_REGISTRY_ATTR,
    CACHE_REGISTRY_ATTR,
    CacheEvictInfo,
    CacheInfo,
    cache,
    cache_evict,
    get_cache_evict_info,
    get_cache_info,
)


class TestCacheDecorator:
    """Tests for @cache decorator."""

    def test_cache_decorator_adds_metadata(self) -> None:
        """Test that @cache adds CacheInfo metadata to function."""

        @cache(key="user:{id}", ttl=300)
        async def get_user(id: int) -> dict:
            return {"id": id}

        assert hasattr(get_user, CACHE_REGISTRY_ATTR)
        infos = getattr(get_user, CACHE_REGISTRY_ATTR)
        assert len(infos) == 1
        assert infos[0].key == "user:{id}"
        assert infos[0].ttl == 300

    def test_cache_decorator_without_ttl(self) -> None:
        """Test @cache without TTL."""

        @cache(key="users:list")
        async def list_users() -> list:
            return []

        infos = get_cache_info(list_users)
        assert len(infos) == 1
        assert infos[0].key == "users:list"
        assert infos[0].ttl is None

    def test_cache_decorator_stacking(self) -> None:
        """Test multiple @cache decorators on same function."""

        @cache(key="cache1", ttl=100)
        @cache(key="cache2", ttl=200)
        async def multi_cached() -> dict:
            return {}

        infos = get_cache_info(multi_cached)
        assert len(infos) == 2
        # First decorator is outermost, last to be applied
        assert infos[0].key == "cache2"
        assert infos[1].key == "cache1"

    def test_get_cache_info_no_decorator(self) -> None:
        """Test get_cache_info returns empty list for non-decorated function."""

        async def plain_func() -> dict:
            return {}

        infos = get_cache_info(plain_func)
        assert infos == []


class TestCacheEvictDecorator:
    """Tests for @cache_evict decorator."""

    def test_cache_evict_decorator_adds_metadata(self) -> None:
        """Test that @cache_evict adds CacheEvictInfo metadata."""

        @cache_evict(key="user:{id}")
        async def update_user(id: int) -> dict:
            return {"id": id}

        assert hasattr(update_user, CACHE_EVICT_REGISTRY_ATTR)
        infos = getattr(update_user, CACHE_EVICT_REGISTRY_ATTR)
        assert len(infos) == 1
        assert infos[0].key == "user:{id}"
        assert infos[0].all_entries is False

    def test_cache_evict_with_all_entries(self) -> None:
        """Test @cache_evict with all_entries=True."""

        @cache_evict(key="user:*", all_entries=True)
        async def delete_all_users() -> dict:
            return {"deleted": True}

        infos = get_cache_evict_info(delete_all_users)
        assert len(infos) == 1
        assert infos[0].key == "user:*"
        assert infos[0].all_entries is True

    def test_cache_evict_decorator_stacking(self) -> None:
        """Test multiple @cache_evict decorators on same function."""

        @cache_evict(key="user:{id}")
        @cache_evict(key="users:list")
        async def update_user(id: int) -> dict:
            return {"id": id}

        infos = get_cache_evict_info(update_user)
        assert len(infos) == 2

    def test_get_cache_evict_info_no_decorator(self) -> None:
        """Test get_cache_evict_info returns empty list for non-decorated function."""

        async def plain_func() -> dict:
            return {}

        infos = get_cache_evict_info(plain_func)
        assert infos == []


class TestCacheAndEvictTogether:
    """Tests for combining @cache and @cache_evict."""

    def test_both_decorators_on_same_function(self) -> None:
        """Test @cache and @cache_evict on the same function."""

        @cache(key="computed:{id}", ttl=300)
        @cache_evict(key="raw:{id}")
        async def process_data(id: int) -> dict:
            return {"id": id, "processed": True}

        cache_infos = get_cache_info(process_data)
        evict_infos = get_cache_evict_info(process_data)

        assert len(cache_infos) == 1
        assert cache_infos[0].key == "computed:{id}"

        assert len(evict_infos) == 1
        assert evict_infos[0].key == "raw:{id}"


class TestCacheInfo:
    """Tests for CacheInfo dataclass."""

    def test_cache_info_defaults(self) -> None:
        """Test CacheInfo default values."""
        info = CacheInfo(key="test")
        assert info.key == "test"
        assert info.ttl is None

    def test_cache_info_with_ttl(self) -> None:
        """Test CacheInfo with TTL."""
        info = CacheInfo(key="test", ttl=300)
        assert info.key == "test"
        assert info.ttl == 300


class TestCacheEvictInfo:
    """Tests for CacheEvictInfo dataclass."""

    def test_cache_evict_info_defaults(self) -> None:
        """Test CacheEvictInfo default values."""
        info = CacheEvictInfo(key="test")
        assert info.key == "test"
        assert info.all_entries is False

    def test_cache_evict_info_with_all_entries(self) -> None:
        """Test CacheEvictInfo with all_entries=True."""
        info = CacheEvictInfo(key="test:*", all_entries=True)
        assert info.key == "test:*"
        assert info.all_entries is True
