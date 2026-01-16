"""Tests for type coercion."""

from datetime import date, datetime
from uuid import UUID

import pytest

from pykour.schema.types import coerce_value


class TestIntCoercion:
    """Tests for int coercion."""

    def test_int_from_int(self) -> None:
        """Int should pass through."""
        assert coerce_value(42, int) == 42

    def test_int_from_string(self) -> None:
        """String should coerce to int."""
        assert coerce_value("123", int) == 123

    def test_int_from_negative_string(self) -> None:
        """Negative string should coerce to int."""
        assert coerce_value("-42", int) == -42

    def test_int_from_bool_raises(self) -> None:
        """Bool should not coerce to int."""
        with pytest.raises(TypeError):
            coerce_value(True, int)

    def test_int_from_invalid_string_raises(self) -> None:
        """Invalid string should raise."""
        with pytest.raises(ValueError):
            coerce_value("abc", int)


class TestFloatCoercion:
    """Tests for float coercion."""

    def test_float_from_float(self) -> None:
        """Float should pass through."""
        assert coerce_value(3.14, float) == 3.14

    def test_float_from_int(self) -> None:
        """Int should coerce to float."""
        assert coerce_value(42, float) == 42.0

    def test_float_from_string(self) -> None:
        """String should coerce to float."""
        assert coerce_value("3.14", float) == 3.14


class TestBoolCoercion:
    """Tests for bool coercion."""

    def test_bool_from_bool(self) -> None:
        """Bool should pass through."""
        assert coerce_value(True, bool) is True
        assert coerce_value(False, bool) is False

    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "on"])
    def test_truthy_strings(self, value: str) -> None:
        """Truthy strings should coerce to True."""
        assert coerce_value(value, bool) is True

    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "no", "off"])
    def test_falsy_strings(self, value: str) -> None:
        """Falsy strings should coerce to False."""
        assert coerce_value(value, bool) is False

    def test_invalid_string_raises(self) -> None:
        """Invalid bool string should raise."""
        with pytest.raises(ValueError):
            coerce_value("maybe", bool)


class TestStrCoercion:
    """Tests for str coercion."""

    def test_str_from_str(self) -> None:
        """String should pass through."""
        assert coerce_value("hello", str) == "hello"

    def test_str_from_int(self) -> None:
        """Int should coerce to string."""
        assert coerce_value(42, str) == "42"


class TestUUIDCoercion:
    """Tests for UUID coercion."""

    def test_uuid_from_uuid(self) -> None:
        """UUID should pass through."""
        uid = UUID("550e8400-e29b-41d4-a716-446655440000")
        assert coerce_value(uid, UUID) == uid

    def test_uuid_from_string(self) -> None:
        """String should coerce to UUID."""
        result = coerce_value("550e8400-e29b-41d4-a716-446655440000", UUID)
        assert isinstance(result, UUID)

    def test_uuid_invalid_string_raises(self) -> None:
        """Invalid UUID string should raise."""
        with pytest.raises(ValueError):
            coerce_value("not-a-uuid", UUID)


class TestDatetimeCoercion:
    """Tests for datetime coercion."""

    def test_datetime_from_datetime(self) -> None:
        """Datetime should pass through."""
        dt = datetime(2024, 1, 15, 12, 30, 0)
        assert coerce_value(dt, datetime) == dt

    def test_datetime_from_iso_string(self) -> None:
        """ISO string should coerce to datetime."""
        result = coerce_value("2024-01-15T12:30:00", datetime)
        assert result == datetime(2024, 1, 15, 12, 30, 0)


class TestDateCoercion:
    """Tests for date coercion."""

    def test_date_from_date(self) -> None:
        """Date should pass through."""
        d = date(2024, 1, 15)
        assert coerce_value(d, date) == d

    def test_date_from_iso_string(self) -> None:
        """ISO string should coerce to date."""
        result = coerce_value("2024-01-15", date)
        assert result == date(2024, 1, 15)


class TestOptionalCoercion:
    """Tests for Optional type coercion."""

    def test_none_for_optional(self) -> None:
        """None should be allowed for Optional."""
        assert coerce_value(None, int | None) is None

    def test_value_for_optional(self) -> None:
        """Value should coerce for Optional."""
        assert coerce_value("42", int | None) == 42


class TestListCoercion:
    """Tests for list type coercion."""

    def test_list_of_ints(self) -> None:
        """List of strings should coerce to list of ints."""
        assert coerce_value(["1", "2", "3"], list[int]) == [1, 2, 3]

    def test_list_of_strings(self) -> None:
        """List of strings should pass through."""
        assert coerce_value(["a", "b"], list[str]) == ["a", "b"]

    def test_non_list_raises(self) -> None:
        """Non-list should raise TypeError."""
        with pytest.raises(TypeError):
            coerce_value("not a list", list[int])


class TestDictCoercion:
    """Tests for dict type coercion."""

    def test_dict_passthrough(self) -> None:
        """Dict should pass through."""
        data = {"a": "1", "b": "2"}
        assert coerce_value(data, dict[str, str]) == data

    def test_non_dict_raises(self) -> None:
        """Non-dict should raise TypeError."""
        with pytest.raises(TypeError):
            coerce_value("not a dict", dict[str, str])
