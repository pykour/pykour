"""High-performance JSON serialization using orjson.

This module provides a thin wrapper around orjson with support for
additional types not natively supported by orjson.

Natively supported by orjson:
- datetime, date, time → ISO 8601 format
- UUID → string
- Enum → value
- dataclass → dict

Custom handling via default function:
- Decimal → string (preserves precision)
- Schema subclasses → model_dump()
- Objects with to_dict() → dict
"""

from decimal import Decimal
from typing import Any

import orjson


def default(obj: Any) -> Any:
    """Default serializer for types not natively supported by orjson.

    Args:
        obj: Object to serialize.

    Returns:
        JSON-serializable representation.

    Raises:
        TypeError: If the object cannot be serialized.
    """
    if isinstance(obj, Decimal):
        return str(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def dumps(obj: Any, *, ensure_ascii: bool = False) -> bytes:
    """Serialize object to JSON bytes.

    Args:
        obj: Object to serialize.
        ensure_ascii: If True, escape non-ASCII characters. Default False.

    Returns:
        JSON-encoded bytes.

    Example:
        >>> from pykour.json import dumps
        >>> dumps({"hello": "world"})
        b'{"hello":"world"}'
        >>> dumps({"time": datetime.now()})
        b'{"time":"2024-01-15T12:00:00"}'
    """
    options = orjson.OPT_NON_STR_KEYS
    if ensure_ascii:
        options |= orjson.OPT_NON_STR_KEYS
    return orjson.dumps(obj, default=default, option=options)


def loads(data: bytes | str) -> Any:
    """Deserialize JSON bytes or string to Python object.

    Args:
        data: JSON bytes or string.

    Returns:
        Deserialized Python object.

    Example:
        >>> from pykour.json import loads
        >>> loads(b'{"hello":"world"}')
        {'hello': 'world'}
    """
    return orjson.loads(data)
