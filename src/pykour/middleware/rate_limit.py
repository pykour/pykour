"""Rate limiting middleware for Pykour."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable

from pykour.common.storage import BaseInMemoryStorage
from pykour.middleware.base import BaseMiddleware
from pykour.middleware.utils import is_path_excluded
from pykour.response import JSONResponse
from pykour.types import Message, Receive, Scope, Send


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting.

    Attributes:
        requests_per_second: Maximum requests per second.
        burst_size: Maximum burst size (bucket capacity).
    """

    requests_per_second: float
    burst_size: int

    def __post_init__(self) -> None:
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        if self.burst_size <= 0:
            raise ValueError("burst_size must be positive")


class RateLimitStorage(ABC):
    """Abstract base class for rate limit storage backends."""

    @abstractmethod
    async def get_tokens(
        self, key: str, config: RateLimitConfig
    ) -> tuple[float, float]:
        """Get current tokens and last update time.

        Args:
            key: The rate limit key (e.g., client IP).
            config: Rate limit configuration.

        Returns:
            Tuple of (tokens, last_update_time).
        """
        ...

    @abstractmethod
    async def set_tokens(self, key: str, tokens: float, timestamp: float) -> None:
        """Set tokens and update time.

        Args:
            key: The rate limit key.
            tokens: Current token count.
            timestamp: Update timestamp.
        """
        ...

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up expired entries."""
        ...


class RateLimitInMemoryStorage(
    BaseInMemoryStorage[tuple[float, float]], RateLimitStorage
):
    """In-memory storage for rate limiting.

    Uses a dictionary to store token bucket state.
    Suitable for single-instance deployments.
    Inherits from BaseInMemoryStorage for common lock/cleanup functionality.
    """

    # Time in seconds after which entries are considered stale
    _ENTRY_EXPIRY_TIME = 300.0  # 5 minutes

    def __init__(self, cleanup_interval: float = 60.0) -> None:
        """Initialize in-memory storage.

        Args:
            cleanup_interval: Interval in seconds between cleanup runs.
        """
        super().__init__(cleanup_interval=cleanup_interval)
        self._last_cleanup = time.time()

    def _cleanup_expired_entries(self) -> list[str]:
        """Identify stale rate limit entries for cleanup."""
        cutoff = time.time() - self._ENTRY_EXPIRY_TIME
        return [key for key, (_, timestamp) in self._data.items() if timestamp < cutoff]

    async def get_tokens(
        self, key: str, config: RateLimitConfig
    ) -> tuple[float, float]:
        """Get current tokens and last update time."""
        async with self._lock:
            if key in self._data:
                return self._data[key]
            # Initialize with full bucket
            return (float(config.burst_size), time.time())

    async def set_tokens(self, key: str, tokens: float, timestamp: float) -> None:
        """Set tokens and update time."""
        async with self._lock:
            self._data[key] = (tokens, timestamp)

    async def cleanup(self) -> None:
        """Remove entries that haven't been accessed recently."""
        async with self._lock:
            await self._maybe_cleanup()


# Backward compatibility alias
InMemoryStorage = RateLimitInMemoryStorage


class TokenBucket:
    """Token bucket rate limiter.

    The token bucket algorithm allows bursts of traffic while maintaining
    an average rate limit. Tokens are added at a constant rate up to a
    maximum (burst_size), and each request consumes one token.

    Thread-safety: Uses per-key locks to ensure atomic read-modify-write
    operations, preventing race conditions when multiple coroutines access
    the same key concurrently.
    """

    # Time in seconds after which unused locks are cleaned up
    _LOCK_CLEANUP_INTERVAL = 60.0
    _LOCK_EXPIRY_TIME = 300.0  # 5 minutes

    def __init__(
        self,
        storage: RateLimitStorage,
        config: RateLimitConfig,
    ) -> None:
        """Initialize token bucket.

        Args:
            storage: Storage backend for token state.
            config: Rate limit configuration.
        """
        self.storage = storage
        self.config = config
        self._locks: dict[str, asyncio.Lock] = {}
        self._lock_last_used: dict[str, float] = {}
        self._last_lock_cleanup = time.time()

    def _get_lock(self, key: str) -> asyncio.Lock:
        """Get or create a lock for a key.

        This method is synchronous (no await) to ensure atomicity in asyncio's
        cooperative multitasking model - no context switch can occur between
        checking and creating the lock.

        Args:
            key: The rate limit key.

        Returns:
            Lock for the given key.
        """
        current_time = time.time()
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        self._lock_last_used[key] = current_time
        return self._locks[key]

    def _cleanup_locks(self) -> None:
        """Remove locks that haven't been used recently.

        Only removes locks that are not currently held to avoid race conditions.
        This method is synchronous to ensure atomicity.
        """
        current_time = time.time()

        # Check cleanup interval
        if current_time - self._last_lock_cleanup < self._LOCK_CLEANUP_INTERVAL:
            return

        self._last_lock_cleanup = current_time
        cutoff = current_time - self._LOCK_EXPIRY_TIME

        # Find keys to remove (not recently used and not currently locked)
        keys_to_remove = [
            key
            for key, last_used in self._lock_last_used.items()
            if last_used < cutoff and not self._locks.get(key, asyncio.Lock()).locked()
        ]

        for key in keys_to_remove:
            # Double-check the lock is not held before removing
            lock = self._locks.get(key)
            if lock and not lock.locked():
                del self._locks[key]
                del self._lock_last_used[key]

    async def acquire(self, key: str) -> tuple[bool, float]:
        """Try to acquire a token.

        Uses per-key locking to ensure atomic read-modify-write, preventing
        race conditions when multiple coroutines access the same key.

        Args:
            key: The rate limit key.

        Returns:
            Tuple of (allowed, retry_after_seconds).
            If allowed is True, retry_after is 0.
            If allowed is False, retry_after indicates when to retry.
        """
        lock = self._get_lock(key)

        # Periodically cleanup unused locks
        self._cleanup_locks()

        async with lock:
            current_time = time.time()
            tokens, last_update = await self.storage.get_tokens(key, self.config)

            # Calculate tokens to add based on elapsed time
            elapsed = current_time - last_update
            tokens_to_add = elapsed * self.config.requests_per_second
            tokens = min(tokens + tokens_to_add, float(self.config.burst_size))

            if tokens >= 1.0:
                # Consume a token
                tokens -= 1.0
                await self.storage.set_tokens(key, tokens, current_time)
                return (True, 0.0)
            else:
                # Calculate retry-after time
                tokens_needed = 1.0 - tokens
                retry_after = tokens_needed / self.config.requests_per_second
                await self.storage.set_tokens(key, tokens, current_time)
                return (False, retry_after)


# Type alias for key extractor function
KeyExtractor = Callable[[Scope], str]


def default_key_extractor(scope: Scope) -> str:
    """Extract client IP from scope for rate limiting key.

    Uses the direct client IP from the ASGI scope. Does NOT check
    X-Forwarded-For header by default to prevent IP spoofing attacks.

    For applications behind a reverse proxy, use create_key_extractor()
    with trusted_proxies to safely extract the original client IP.

    Args:
        scope: ASGI scope.

    Returns:
        Client identifier string.
    """
    client = scope.get("client")
    if client:
        return client[0]
    return "unknown"


def create_key_extractor(
    trusted_proxies: set[str] | list[str] | None = None,
) -> KeyExtractor:
    """Create a key extractor with trusted proxy support.

    Returns a key extractor function that safely extracts the client IP,
    only trusting X-Forwarded-For headers when the immediate client is
    a known trusted proxy.

    Security Note:
        X-Forwarded-For can be spoofed by clients. Only trust this header
        when the request comes from a known proxy server. If trusted_proxies
        is None or empty, X-Forwarded-For is never used.

    Args:
        trusted_proxies: Set of IP addresses of trusted reverse proxies.
            When the immediate client IP is in this set, the first IP from
            X-Forwarded-For header is used. Common values include:
            - {"127.0.0.1", "::1"} for local proxies
            - {"10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"} for private networks
            Note: CIDR notation is NOT supported; use exact IP addresses.

    Returns:
        A key extractor function suitable for RateLimitMiddleware.

    Example:
        # Trust requests from localhost proxy
        app.add_middleware(
            RateLimitMiddleware,
            key_extractor=create_key_extractor(
                trusted_proxies={"127.0.0.1", "::1"}
            ),
        )
    """
    trusted: set[str] = set(trusted_proxies) if trusted_proxies else set()

    def extractor(scope: Scope) -> str:
        client = scope.get("client")
        if not client:
            return "unknown"

        client_ip = client[0]

        # Only check X-Forwarded-For if client is a trusted proxy
        if trusted and client_ip in trusted:
            headers = dict(scope.get("headers", []))
            forwarded_for = headers.get(b"x-forwarded-for", b"").decode("latin-1")
            if forwarded_for:
                # Get the first IP in the chain (original client)
                original_ip = forwarded_for.split(",")[0].strip()
                if original_ip:
                    return original_ip

        return client_ip

    return extractor


class RateLimitMiddleware(BaseMiddleware):
    """Rate limiting middleware using token bucket algorithm.

    Example:
        # Basic usage with defaults (10 requests/second, burst of 20)
        app.add_middleware(RateLimitMiddleware)

        # Custom configuration
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_second=5,
            burst_size=10,
        )

        # Path-specific rate limits
        app.add_middleware(
            RateLimitMiddleware,
            path_configs={
                "/api/login": RateLimitConfig(1, 3),  # Stricter for login
                "/api/": RateLimitConfig(10, 30),     # Prefix match
            },
        )

        # Custom key extractor (e.g., by user ID)
        app.add_middleware(
            RateLimitMiddleware,
            key_extractor=lambda scope: scope.get("user", {}).get("id", "anonymous"),
        )
    """

    def __init__(
        self,
        app: Any,
        *,
        requests_per_second: float = 10.0,
        burst_size: int = 20,
        storage: RateLimitStorage | None = None,
        key_extractor: KeyExtractor | None = None,
        path_configs: dict[str, RateLimitConfig] | None = None,
        exclude_paths: list[str] | None = None,
        include_headers: bool = True,
    ) -> None:
        """Initialize rate limit middleware.

        Args:
            app: The ASGI application to wrap.
            requests_per_second: Default requests per second limit.
            burst_size: Default burst size (max tokens).
            storage: Storage backend (defaults to InMemoryStorage).
            key_extractor: Function to extract rate limit key from scope.
            path_configs: Path-specific rate limit configurations.
                          Supports prefix matching (e.g., "/api/" matches "/api/users").
            exclude_paths: Paths to exclude from rate limiting.
            include_headers: Whether to include rate limit headers in response.
        """
        super().__init__(app)
        self.default_config = RateLimitConfig(requests_per_second, burst_size)
        self.storage = storage or InMemoryStorage()
        self.key_extractor = key_extractor or default_key_extractor
        self.path_configs = path_configs or {}
        self.exclude_paths = list(exclude_paths or [])
        self.include_headers = include_headers
        self._buckets: dict[str, TokenBucket] = {}

    def _get_config_for_path(self, path: str) -> RateLimitConfig:
        """Get rate limit config for a path.

        First checks for exact match, then prefix match.

        Args:
            path: Request path.

        Returns:
            Rate limit configuration.
        """
        # Exact match first
        if path in self.path_configs:
            return self.path_configs[path]

        # Prefix match (longest prefix wins)
        matching_prefix = ""
        matching_config = self.default_config

        for prefix, config in self.path_configs.items():
            if path.startswith(prefix) and len(prefix) > len(matching_prefix):
                matching_prefix = prefix
                matching_config = config

        return matching_config

    def _should_rate_limit(self, path: str) -> bool:
        """Check if path should be rate limited.

        Args:
            path: Request path.

        Returns:
            True if should apply rate limiting.
        """
        return not is_path_excluded(path, self.exclude_paths)

    def _get_bucket(self, config: RateLimitConfig) -> TokenBucket:
        """Get or create a token bucket for config.

        Args:
            config: Rate limit configuration.

        Returns:
            Token bucket instance.
        """
        config_key = f"{config.requests_per_second}:{config.burst_size}"
        if config_key not in self._buckets:
            self._buckets[config_key] = TokenBucket(self.storage, config)
        return self._buckets[config_key]

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request with rate limiting."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")

        # Skip rate limiting for excluded paths
        if not self._should_rate_limit(path):
            await self.app(scope, receive, send)
            return

        # Get config and bucket for this path
        config = self._get_config_for_path(path)
        bucket = self._get_bucket(config)

        # Extract rate limit key
        key = self.key_extractor(scope)

        # Try to acquire a token
        allowed, retry_after = await bucket.acquire(key)

        # Periodically cleanup storage
        await self.storage.cleanup()

        if not allowed:
            # Rate limit exceeded
            response_headers: dict[str, str] | None = None
            if self.include_headers:
                response_headers = {
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(config.burst_size),
                    "X-RateLimit-Remaining": "0",
                }

            response = JSONResponse(
                content={
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after": round(retry_after, 2),
                },
                status_code=429,
                headers=response_headers,
            )

            await response(scope, receive, send)
            return

        if self.include_headers:
            # Wrap send to inject rate limit headers
            original_send = send

            async def send_with_headers(message: Message) -> None:
                if message["type"] == "http.response.start":
                    headers = list(message.get("headers", []))
                    headers.append(
                        (b"x-ratelimit-limit", str(config.burst_size).encode())
                    )
                    # Note: Remaining is approximate due to concurrent requests
                    headers.append((b"x-ratelimit-remaining", b"*"))
                    message = {**message, "headers": headers}
                await original_send(message)

            send = send_with_headers

        await self.app(scope, receive, send)
