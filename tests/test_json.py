"""Tests for pykour.json module."""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, time, timezone
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

import pytest

from pykour import json as pykour_json
from pykour.schema import Schema


class TestDumpsBasic:
    """Test basic JSON serialization."""

    def test_dumps_dict(self) -> None:
        """Serialize a dictionary."""
        data = {"name": "test", "value": 123}
        result = pykour_json.dumps(data)
        assert isinstance(result, bytes)
        assert pykour_json.loads(result) == data

    def test_dumps_list(self) -> None:
        """Serialize a list."""
        data = [1, 2, 3, "four"]
        result = pykour_json.dumps(data)
        assert pykour_json.loads(result) == data

    def test_dumps_nested(self) -> None:
        """Serialize nested structures."""
        data = {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
        result = pykour_json.dumps(data)
        assert pykour_json.loads(result) == data

    def test_dumps_unicode(self) -> None:
        """Serialize Unicode characters."""
        data = {"message": "こんにちは世界"}
        result = pykour_json.dumps(data)
        # By default, ensure_ascii=False, so Unicode is preserved
        assert "こんにちは世界".encode() in result

    def test_dumps_ensure_ascii(self) -> None:
        """Serialize with ASCII escaping."""
        data = {"message": "日本語"}
        result = pykour_json.dumps(data, ensure_ascii=True)
        # With ensure_ascii=True, should still work
        assert pykour_json.loads(result) == data


class TestDumpsDatetime:
    """Test datetime serialization."""

    def test_dumps_datetime(self) -> None:
        """Serialize datetime to ISO 8601."""
        dt = datetime(2024, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        data = {"timestamp": dt}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["timestamp"] == "2024-01-15T12:30:45+00:00"

    def test_dumps_date(self) -> None:
        """Serialize date to ISO 8601."""
        d = date(2024, 1, 15)
        data = {"date": d}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["date"] == "2024-01-15"

    def test_dumps_time(self) -> None:
        """Serialize time to ISO 8601."""
        t = time(12, 30, 45)
        data = {"time": t}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["time"] == "12:30:45"


class TestDumpsUUID:
    """Test UUID serialization."""

    def test_dumps_uuid(self) -> None:
        """Serialize UUID to string."""
        uid = UUID("12345678-1234-5678-1234-567812345678")
        data = {"id": uid}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["id"] == "12345678-1234-5678-1234-567812345678"


class TestDumpsDecimal:
    """Test Decimal serialization."""

    def test_dumps_decimal(self) -> None:
        """Serialize Decimal to string."""
        dec = Decimal("123.45")
        data = {"price": dec}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["price"] == "123.45"

    def test_dumps_decimal_precision(self) -> None:
        """Preserve Decimal precision."""
        dec = Decimal("0.123456789012345678901234567890")
        data = {"value": dec}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["value"] == "0.123456789012345678901234567890"


class TestDumpsEnum:
    """Test Enum serialization."""

    def test_dumps_string_enum(self) -> None:
        """Serialize string Enum to value."""

        class Status(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        data = {"status": Status.ACTIVE}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["status"] == "active"

    def test_dumps_int_enum(self) -> None:
        """Serialize int Enum to value."""

        class Priority(int, Enum):
            LOW = 1
            MEDIUM = 2
            HIGH = 3

        data = {"priority": Priority.HIGH}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["priority"] == 3


class TestDumpsDataclass:
    """Test dataclass serialization."""

    def test_dumps_dataclass(self) -> None:
        """Serialize dataclass to dict."""

        @dataclasses.dataclass
        class User:
            id: int
            name: str
            active: bool = True

        user = User(id=1, name="Alice")
        data = {"user": user}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["user"] == {"id": 1, "name": "Alice", "active": True}

    def test_dumps_nested_dataclass(self) -> None:
        """Serialize nested dataclass."""

        @dataclasses.dataclass
        class Address:
            city: str
            country: str

        @dataclasses.dataclass
        class Person:
            name: str
            address: Address

        person = Person(name="Bob", address=Address(city="Tokyo", country="Japan"))
        result = pykour_json.dumps(person)
        parsed = pykour_json.loads(result)
        assert parsed == {
            "name": "Bob",
            "address": {"city": "Tokyo", "country": "Japan"},
        }


class TestDumpsSchema:
    """Test Schema serialization."""

    def test_dumps_schema(self) -> None:
        """Serialize Schema subclass using model_dump."""

        class UserSchema(Schema):
            name: str
            age: int

        schema = UserSchema(name="Charlie", age=30)
        data = {"user": schema}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["user"] == {"name": "Charlie", "age": 30}


class TestLoads:
    """Test JSON deserialization."""

    def test_loads_bytes(self) -> None:
        """Deserialize from bytes."""
        data = b'{"name": "test"}'
        result = pykour_json.loads(data)
        assert result == {"name": "test"}

    def test_loads_str(self) -> None:
        """Deserialize from string."""
        data = '{"name": "test"}'
        result = pykour_json.loads(data)
        assert result == {"name": "test"}

    def test_loads_unicode(self) -> None:
        """Deserialize Unicode content."""
        data = '{"message": "こんにちは"}'
        result = pykour_json.loads(data)
        assert result["message"] == "こんにちは"


class TestDumpsUnsupportedType:
    """Test handling of unsupported types."""

    def test_dumps_unsupported_type_raises(self) -> None:
        """Unsupported types raise TypeError."""

        class CustomObject:
            pass

        data = {"obj": CustomObject()}
        with pytest.raises(TypeError, match="is not JSON serializable"):
            pykour_json.dumps(data)


class TestCustomDefaultHandlers:
    """Test custom default handlers (model_dump, to_dict)."""

    def test_dumps_object_with_model_dump(self) -> None:
        """Objects with model_dump() method are serialized correctly."""

        class CustomModel:
            def __init__(self, value: int) -> None:
                self._value = value

            def model_dump(self) -> dict[str, Any]:
                return {"value": self._value}

        obj = CustomModel(42)
        data = {"model": obj}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["model"] == {"value": 42}

    def test_dumps_object_with_to_dict(self) -> None:
        """Objects with to_dict() method are serialized correctly."""

        class LegacyModel:
            def __init__(self, name: str) -> None:
                self._name = name

            def to_dict(self) -> dict[str, Any]:
                return {"name": self._name}

        obj = LegacyModel("test")
        data = {"model": obj}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        assert parsed["model"] == {"name": "test"}


class TestNonStrKeys:
    """Test non-string key support."""

    def test_dumps_int_keys(self) -> None:
        """Integer keys are converted to strings."""
        data = {1: "one", 2: "two"}
        result = pykour_json.dumps(data)
        parsed = pykour_json.loads(result)
        # JSON keys are always strings
        assert parsed == {"1": "one", "2": "two"}
