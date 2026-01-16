"""Cache-specific exceptions."""


class CacheException(Exception):
    """Base exception for cache operations."""

    pass


class CacheConnectionException(CacheException):
    """Exception raised when cache connection fails."""

    pass


class CacheSerializationException(CacheException):
    """Exception raised when serialization/deserialization fails."""

    pass


class CacheKeyException(CacheException):
    """Exception raised when cache key is invalid."""

    pass


# Backward compatibility aliases
CacheError = CacheException
CacheConnectionError = CacheConnectionException
CacheSerializationError = CacheSerializationException
CacheKeyError = CacheKeyException
