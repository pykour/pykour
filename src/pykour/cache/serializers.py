"""Cache value serializers."""

from __future__ import annotations

import pickle
from abc import ABC, abstractmethod
from typing import Any, TypeVar

import orjson

from pykour import json as pykour_json
from pykour.cache.exceptions import CacheSerializationError

T = TypeVar("T")


class Serializer(ABC):
    """Abstract base class for cache value serializers."""

    @abstractmethod
    def serialize(self, value: Any) -> bytes:
        """Serialize a value to bytes.

        Args:
            value: The value to serialize.

        Returns:
            Serialized bytes.

        Raises:
            CacheSerializationError: If serialization fails.
        """
        ...

    @abstractmethod
    def deserialize(self, data: bytes, type_: type[T] | None = None) -> Any:
        """Deserialize bytes to a value.

        Args:
            data: The bytes to deserialize.
            type_: Optional type hint for deserialization.

        Returns:
            Deserialized value.

        Raises:
            CacheSerializationError: If deserialization fails.
        """
        ...


class JSONSerializer(Serializer):
    """JSON serializer for cache values.

    Suitable for JSON-serializable data (dicts, lists, strings, numbers, booleans).
    """

    def __init__(self, ensure_ascii: bool = False) -> None:
        """Initialize JSON serializer.

        Args:
            ensure_ascii: If True, escape non-ASCII characters. Default False.
        """
        self._ensure_ascii = ensure_ascii

    def serialize(self, value: Any) -> bytes:
        """Serialize a value to JSON bytes."""
        try:
            return pykour_json.dumps(value, ensure_ascii=self._ensure_ascii)
        except TypeError as e:
            raise CacheSerializationError(f"JSON serialization failed: {e}") from e

    def deserialize(self, data: bytes, type_: type[T] | None = None) -> Any:
        """Deserialize JSON bytes to a value."""
        try:
            return pykour_json.loads(data)
        except orjson.JSONDecodeError as e:
            raise CacheSerializationError(f"JSON deserialization failed: {e}") from e


class PickleSerializer(Serializer):
    """Pickle serializer for cache values.

    Suitable for complex Python objects that cannot be JSON-serialized.

    Warning:
        Only use with trusted data sources as pickle can execute arbitrary code.
    """

    def __init__(self, protocol: int | None = None) -> None:
        """Initialize Pickle serializer.

        Args:
            protocol: Pickle protocol version. Default uses highest available.
        """
        self._protocol = protocol

    def serialize(self, value: Any) -> bytes:
        """Serialize a value using pickle."""
        try:
            return pickle.dumps(value, protocol=self._protocol)
        except (pickle.PicklingError, TypeError) as e:
            raise CacheSerializationError(f"Pickle serialization failed: {e}") from e

    def deserialize(self, data: bytes, type_: type[T] | None = None) -> Any:
        """Deserialize pickled bytes to a value."""
        try:
            return pickle.loads(data)  # noqa: S301 - pickle usage is intentional
        except (pickle.UnpicklingError, TypeError) as e:
            raise CacheSerializationError(f"Pickle deserialization failed: {e}") from e
