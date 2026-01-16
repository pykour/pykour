"""Tests for rate limiting middleware functionality."""

import asyncio
import time

import pytest

from tests.helpers import create_noop_receive, create_noop_send
from pykour.middleware.rate_limit import (
    InMemoryStorage,
    RateLimitConfig,
    RateLimitMiddleware,
    TokenBucket,
    create_key_extractor,
    default_key_extractor,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_valid_config(self) -> None:
        """Valid configuration should be accepted."""
        config = RateLimitConfig(10.0, 20)
        assert config.requests_per_second == 10.0
        assert config.burst_size == 20

    def test_invalid_requests_per_second(self) -> None:
        """Zero or negative requests_per_second should raise ValueError."""
        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimitConfig(0, 10)

        with pytest.raises(ValueError, match="requests_per_second must be positive"):
            RateLimitConfig(-1, 10)

    def test_invalid_burst_size(self) -> None:
        """Zero or negative burst_size should raise ValueError."""
        with pytest.raises(ValueError, match="burst_size must be positive"):
            RateLimitConfig(10, 0)

        with pytest.raises(ValueError, match="burst_size must be positive"):
            RateLimitConfig(10, -1)


class TestInMemoryStorage:
    """Tests for InMemoryStorage."""

    @pytest.mark.asyncio
    async def test_initial_tokens(self) -> None:
        """New keys should get full bucket of tokens."""
        storage = InMemoryStorage()
        config = RateLimitConfig(10.0, 20)

        tokens, _ = await storage.get_tokens("new_key", config)
        assert tokens == 20.0

    @pytest.mark.asyncio
    async def test_set_and_get_tokens(self) -> None:
        """Setting tokens should be retrievable."""
        storage = InMemoryStorage()
        config = RateLimitConfig(10.0, 20)

        await storage.set_tokens("test_key", 5.0, 1000.0)
        tokens, timestamp = await storage.get_tokens("test_key", config)

        assert tokens == 5.0
        assert timestamp == 1000.0

    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self) -> None:
        """Cleanup should remove old entries."""
        storage = InMemoryStorage(cleanup_interval=0)

        # Add an old entry
        old_time = time.time() - 400  # 400 seconds ago (> 300 cutoff)
        await storage.set_tokens("old_key", 5.0, old_time)

        # Add a recent entry
        await storage.set_tokens("new_key", 10.0, time.time())

        # Run cleanup
        await storage.cleanup()

        # Old entry should be removed, new should remain
        config = RateLimitConfig(10.0, 20)
        tokens, _ = await storage.get_tokens("old_key", config)
        assert tokens == 20.0  # Reset to full bucket (key was removed)

        tokens, _ = await storage.get_tokens("new_key", config)
        assert tokens == 10.0  # Still has set value


class TestTokenBucket:
    """Tests for TokenBucket algorithm."""

    @pytest.mark.asyncio
    async def test_acquire_with_available_tokens(self) -> None:
        """Should allow request when tokens are available."""
        storage = InMemoryStorage()
        config = RateLimitConfig(10.0, 5)
        bucket = TokenBucket(storage, config)

        allowed, retry_after = await bucket.acquire("test_key")
        assert allowed is True
        assert retry_after == 0.0

    @pytest.mark.asyncio
    async def test_acquire_exhausts_tokens(self) -> None:
        """Should deny request when tokens are exhausted."""
        storage = InMemoryStorage()
        config = RateLimitConfig(10.0, 3)  # 3 tokens max
        bucket = TokenBucket(storage, config)

        # Exhaust all tokens
        for _ in range(3):
            allowed, _ = await bucket.acquire("test_key")
            assert allowed is True

        # Next request should be denied
        allowed, retry_after = await bucket.acquire("test_key")
        assert allowed is False
        assert retry_after > 0

    @pytest.mark.asyncio
    async def test_token_replenishment(self) -> None:
        """Tokens should replenish over time."""
        storage = InMemoryStorage()
        config = RateLimitConfig(1000.0, 2)  # 1000 tokens/sec, burst of 2
        bucket = TokenBucket(storage, config)

        # Use both tokens quickly
        allowed1, _ = await bucket.acquire("test_key")
        allowed2, _ = await bucket.acquire("test_key")
        assert allowed1 is True
        assert allowed2 is True

        # Third request should be denied (no tokens left)
        allowed3, _ = await bucket.acquire("test_key")
        assert allowed3 is False

        # Wait for replenishment (2ms = 2 tokens at 1000/sec)
        await asyncio.sleep(0.003)

        # Should be allowed now
        allowed4, _ = await bucket.acquire("test_key")
        assert allowed4 is True

    @pytest.mark.asyncio
    async def test_different_keys_independent(self) -> None:
        """Different keys should have independent buckets."""
        storage = InMemoryStorage()
        config = RateLimitConfig(10.0, 2)  # 2 tokens burst
        bucket = TokenBucket(storage, config)

        # Exhaust key1 (use 2 tokens)
        allowed1, _ = await bucket.acquire("unique_key_1")
        allowed2, _ = await bucket.acquire("unique_key_1")
        assert allowed1 is True
        assert allowed2 is True

        # key1 should now be exhausted
        allowed3, _ = await bucket.acquire("unique_key_1")
        assert allowed3 is False

        # key2 should have its own bucket with full tokens
        allowed4, _ = await bucket.acquire("unique_key_2")
        assert allowed4 is True

    @pytest.mark.asyncio
    async def test_concurrent_acquire_serialized(self) -> None:
        """Concurrent requests to same key should be serialized by per-key lock.

        This test verifies the race condition fix: without locking, concurrent
        requests could both read the same token count and both succeed, allowing
        more requests than the burst size.
        """
        storage = InMemoryStorage()
        config = RateLimitConfig(10.0, 5)  # 5 tokens burst
        bucket = TokenBucket(storage, config)

        # Launch 10 concurrent requests for the same key
        tasks = [bucket.acquire("concurrent_key") for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # Count allowed requests
        allowed_count = sum(1 for allowed, _ in results if allowed)

        # Should allow exactly burst_size requests, no more
        # Without proper locking, race conditions could allow more than 5
        assert allowed_count == 5

    @pytest.mark.asyncio
    async def test_concurrent_different_keys_independent(self) -> None:
        """Concurrent requests to different keys should not block each other."""
        storage = InMemoryStorage()
        config = RateLimitConfig(10.0, 3)  # 3 tokens burst per key
        bucket = TokenBucket(storage, config)

        # Launch concurrent requests for different keys
        tasks = [
            bucket.acquire("key_a"),
            bucket.acquire("key_b"),
            bucket.acquire("key_a"),
            bucket.acquire("key_b"),
            bucket.acquire("key_a"),
            bucket.acquire("key_b"),
        ]
        results = await asyncio.gather(*tasks)

        # All 6 should be allowed (3 per key)
        allowed_count = sum(1 for allowed, _ in results if allowed)
        assert allowed_count == 6

    @pytest.mark.asyncio
    async def test_lock_cleanup_removes_old_locks(self) -> None:
        """Cleanup should remove locks that haven't been used recently."""
        storage = InMemoryStorage()
        config = RateLimitConfig(10.0, 5)
        bucket = TokenBucket(storage, config)

        # Acquire a token to create a lock
        await bucket.acquire("old_key")
        assert "old_key" in bucket._locks

        # Simulate time passing by manipulating internal state
        old_time = time.time() - 400  # 400 seconds ago (> 300 expiry)
        bucket._lock_last_used["old_key"] = old_time
        bucket._last_lock_cleanup = old_time  # Force cleanup to run

        # Acquire a different key to trigger cleanup
        await bucket.acquire("new_key")

        # Old lock should be removed, new one should exist
        assert "old_key" not in bucket._locks
        assert "old_key" not in bucket._lock_last_used
        assert "new_key" in bucket._locks

    @pytest.mark.asyncio
    async def test_lock_cleanup_preserves_recent_locks(self) -> None:
        """Cleanup should not remove locks that were used recently."""
        storage = InMemoryStorage()
        config = RateLimitConfig(10.0, 5)
        bucket = TokenBucket(storage, config)

        # Acquire tokens for two keys
        await bucket.acquire("key1")
        await bucket.acquire("key2")
        assert "key1" in bucket._locks
        assert "key2" in bucket._locks

        # Force cleanup to run (but locks are recent so shouldn't be removed)
        bucket._last_lock_cleanup = time.time() - 100

        # Acquire another key to trigger cleanup
        await bucket.acquire("key3")

        # All locks should still exist (they were used recently)
        assert "key1" in bucket._locks
        assert "key2" in bucket._locks
        assert "key3" in bucket._locks


class TestDefaultKeyExtractor:
    """Tests for default key extractor function."""

    def test_ignores_x_forwarded_for_by_default(self) -> None:
        """Should ignore X-Forwarded-For and use client IP for security."""
        scope = {
            "headers": [(b"x-forwarded-for", b"1.2.3.4, 5.6.7.8")],
            "client": ("10.0.0.1", 12345),
        }
        key = default_key_extractor(scope)
        # Should use direct client IP, NOT X-Forwarded-For
        assert key == "10.0.0.1"

    def test_extract_from_client(self) -> None:
        """Should extract from client when no X-Forwarded-For."""
        scope = {
            "headers": [],
            "client": ("192.168.1.1", 12345),
        }
        key = default_key_extractor(scope)
        assert key == "192.168.1.1"

    def test_fallback_to_unknown(self) -> None:
        """Should return 'unknown' when no identifying info."""
        scope = {"headers": []}
        key = default_key_extractor(scope)
        assert key == "unknown"


class TestCreateKeyExtractor:
    """Tests for create_key_extractor with trusted proxies."""

    def test_extracts_from_x_forwarded_for_when_trusted(self) -> None:
        """Should extract from X-Forwarded-For when client is trusted proxy."""
        extractor = create_key_extractor(trusted_proxies={"10.0.0.1", "10.0.0.2"})
        scope = {
            "headers": [(b"x-forwarded-for", b"1.2.3.4, 5.6.7.8")],
            "client": ("10.0.0.1", 12345),
        }
        key = extractor(scope)
        # Should use first IP from X-Forwarded-For since client is trusted
        assert key == "1.2.3.4"

    def test_uses_client_ip_when_not_trusted(self) -> None:
        """Should use client IP when client is NOT a trusted proxy."""
        extractor = create_key_extractor(trusted_proxies={"127.0.0.1"})
        scope = {
            "headers": [(b"x-forwarded-for", b"1.2.3.4, 5.6.7.8")],
            "client": ("10.0.0.1", 12345),  # Not in trusted_proxies
        }
        key = extractor(scope)
        # Should use direct client IP, ignoring X-Forwarded-For
        assert key == "10.0.0.1"

    def test_uses_client_ip_when_no_trusted_proxies(self) -> None:
        """Should use client IP when trusted_proxies is empty/None."""
        extractor = create_key_extractor(trusted_proxies=None)
        scope = {
            "headers": [(b"x-forwarded-for", b"1.2.3.4")],
            "client": ("10.0.0.1", 12345),
        }
        key = extractor(scope)
        assert key == "10.0.0.1"

        extractor2 = create_key_extractor(trusted_proxies=[])
        key2 = extractor2(scope)
        assert key2 == "10.0.0.1"

    def test_uses_client_ip_when_no_x_forwarded_for(self) -> None:
        """Should use client IP when X-Forwarded-For is not present."""
        extractor = create_key_extractor(trusted_proxies={"10.0.0.1"})
        scope = {
            "headers": [],
            "client": ("10.0.0.1", 12345),
        }
        key = extractor(scope)
        assert key == "10.0.0.1"

    def test_accepts_list_for_trusted_proxies(self) -> None:
        """Should accept list as trusted_proxies parameter."""
        extractor = create_key_extractor(trusted_proxies=["10.0.0.1"])
        scope = {
            "headers": [(b"x-forwarded-for", b"1.2.3.4")],
            "client": ("10.0.0.1", 12345),
        }
        key = extractor(scope)
        assert key == "1.2.3.4"

    def test_fallback_to_unknown(self) -> None:
        """Should return 'unknown' when no client info."""
        extractor = create_key_extractor(trusted_proxies={"10.0.0.1"})
        scope = {"headers": []}
        key = extractor(scope)
        assert key == "unknown"


class TestRateLimitMiddlewareConfig:
    """Tests for RateLimitMiddleware configuration."""

    def test_default_config(self) -> None:
        """Default configuration should have sensible defaults."""
        middleware = RateLimitMiddleware(None)
        assert middleware.default_config.requests_per_second == 10.0
        assert middleware.default_config.burst_size == 20
        assert middleware.include_headers is True

    def test_custom_config(self) -> None:
        """Custom configuration should be respected."""
        middleware = RateLimitMiddleware(
            None,
            requests_per_second=5.0,
            burst_size=10,
            exclude_paths=["/health"],
            include_headers=False,
        )
        assert middleware.default_config.requests_per_second == 5.0
        assert middleware.default_config.burst_size == 10
        assert "/health" in middleware.exclude_paths
        assert middleware.include_headers is False


class TestRateLimitMiddlewarePathConfig:
    """Tests for path-specific rate limiting."""

    def test_exact_path_match(self) -> None:
        """Exact path should get specific config."""
        middleware = RateLimitMiddleware(
            None,
            path_configs={
                "/api/login": RateLimitConfig(1.0, 3),
            },
        )
        config = middleware._get_config_for_path("/api/login")
        assert config.requests_per_second == 1.0
        assert config.burst_size == 3

    def test_prefix_path_match(self) -> None:
        """Prefix path should match sub-paths."""
        middleware = RateLimitMiddleware(
            None,
            path_configs={
                "/api/": RateLimitConfig(5.0, 10),
            },
        )
        config = middleware._get_config_for_path("/api/users")
        assert config.requests_per_second == 5.0

        config = middleware._get_config_for_path("/api/users/123")
        assert config.requests_per_second == 5.0

    def test_longest_prefix_wins(self) -> None:
        """Longest matching prefix should be used."""
        middleware = RateLimitMiddleware(
            None,
            path_configs={
                "/api/": RateLimitConfig(10.0, 20),
                "/api/admin/": RateLimitConfig(2.0, 5),
            },
        )
        # /api/users should match /api/
        config = middleware._get_config_for_path("/api/users")
        assert config.requests_per_second == 10.0

        # /api/admin/settings should match /api/admin/ (longer prefix)
        config = middleware._get_config_for_path("/api/admin/settings")
        assert config.requests_per_second == 2.0

    def test_default_config_for_unmatched_path(self) -> None:
        """Unmatched paths should use default config."""
        middleware = RateLimitMiddleware(
            None,
            requests_per_second=15.0,
            burst_size=30,
            path_configs={
                "/api/": RateLimitConfig(5.0, 10),
            },
        )
        config = middleware._get_config_for_path("/other/path")
        assert config.requests_per_second == 15.0
        assert config.burst_size == 30


class TestRateLimitMiddlewareExclusion:
    """Tests for path exclusion.

    Note: Uses shared is_path_excluded utility from middleware.utils.
    """

    def test_exact_exclusion(self) -> None:
        """Exact path should be excluded."""
        from pykour.middleware.utils import is_path_excluded

        exclude_paths = ["/health", "/metrics"]
        assert is_path_excluded("/health", exclude_paths) is True
        assert is_path_excluded("/metrics", exclude_paths) is True
        assert is_path_excluded("/api/users", exclude_paths) is False

    def test_prefix_exclusion(self) -> None:
        """Prefix paths should be excluded."""
        from pykour.middleware.utils import is_path_excluded

        # Note: Use path without trailing slash - match_prefix handles subpaths
        exclude_paths = ["/internal"]
        assert is_path_excluded("/internal/health", exclude_paths) is True
        assert is_path_excluded("/internal/metrics", exclude_paths) is True
        assert is_path_excluded("/api/users", exclude_paths) is False


class TestRateLimitMiddlewareIntegration:
    """Integration tests for RateLimitMiddleware."""

    @pytest.mark.asyncio
    async def test_allows_requests_under_limit(self) -> None:
        """Requests under limit should be allowed."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RateLimitMiddleware(
            mock_app,
            requests_per_second=10.0,
            burst_size=5,
        )

        scope = {
            "type": "http",
            "path": "/api/test",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }

        await middleware(scope, create_noop_receive(), mock_send)

        # Should pass through to app
        assert any(m.get("status") == 200 for m in messages_sent)

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self) -> None:
        """Requests over limit should be blocked with 429."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RateLimitMiddleware(
            mock_app,
            requests_per_second=1.0,
            burst_size=2,  # Only 2 requests allowed initially
        )

        scope = {
            "type": "http",
            "path": "/api/test",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }

        # First 2 requests should pass
        for _ in range(2):
            messages_sent.clear()
            await middleware(scope, create_noop_receive(), mock_send)
            assert any(m.get("status") == 200 for m in messages_sent)

        # Third request should be rate limited
        messages_sent.clear()
        await middleware(scope, create_noop_receive(), mock_send)
        assert any(m.get("status") == 429 for m in messages_sent)

    @pytest.mark.asyncio
    async def test_excludes_paths(self) -> None:
        """Excluded paths should not be rate limited."""
        request_count = 0

        async def mock_app(scope, receive, send):
            nonlocal request_count
            request_count += 1
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            pass

        middleware = RateLimitMiddleware(
            mock_app,
            requests_per_second=1.0,
            burst_size=1,
            exclude_paths=["/health"],
        )

        scope = {
            "type": "http",
            "path": "/health",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }

        # Should allow unlimited requests to excluded path
        for _ in range(10):
            await middleware(scope, create_noop_receive(), mock_send)

        assert request_count == 10

    @pytest.mark.asyncio
    async def test_non_http_passthrough(self) -> None:
        """Non-HTTP requests should pass through without rate limiting."""
        app_called = False

        async def mock_app(scope, receive, send):
            nonlocal app_called
            app_called = True

        middleware = RateLimitMiddleware(mock_app)

        scope = {"type": "websocket", "path": "/ws"}

        await middleware(scope, create_noop_receive(), create_noop_send())
        assert app_called is True

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self) -> None:
        """Rate limit headers should be included when enabled."""
        messages_sent: list[dict] = []

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            messages_sent.append(message)

        middleware = RateLimitMiddleware(
            mock_app,
            burst_size=10,
            include_headers=True,
        )

        scope = {
            "type": "http",
            "path": "/api/test",
            "headers": [],
            "client": ("127.0.0.1", 12345),
        }

        await middleware(scope, create_noop_receive(), mock_send)

        # Find response start message
        start_msg = next(
            m for m in messages_sent if m.get("type") == "http.response.start"
        )
        headers = dict(start_msg.get("headers", []))

        assert b"x-ratelimit-limit" in headers
        assert headers[b"x-ratelimit-limit"] == b"10"

    @pytest.mark.asyncio
    async def test_custom_key_extractor(self) -> None:
        """Custom key extractor should be used."""
        keys_used: list[str] = []

        def custom_extractor(scope):
            key = scope.get("custom_key", "default")
            keys_used.append(key)
            return key

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"OK"})

        async def mock_send(message):
            pass

        middleware = RateLimitMiddleware(
            mock_app,
            key_extractor=custom_extractor,
        )

        scope = {
            "type": "http",
            "path": "/api/test",
            "headers": [],
            "custom_key": "user_123",
        }

        await middleware(scope, create_noop_receive(), mock_send)

        assert "user_123" in keys_used
