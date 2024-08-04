import pytest
from pykour.util import cast
from datetime import datetime
from enum import Enum


def test_cast():
    assert cast("1", int) == 1
    assert cast("1.0", float) == 1.0
    assert cast("true", bool) is True
    assert cast("2020-01-01", datetime) == datetime(2020, 1, 1)
    assert cast("2020-01-01", str) == "2020-01-01"

    class TestEnum(Enum):
        A = 1
        B = 2

    assert cast("A", TestEnum) == TestEnum.A
    assert cast("B", TestEnum) == TestEnum.B

    with pytest.raises(ValueError):
        cast("C", TestEnum)

    with pytest.raises(ValueError):
        cast("1", datetime)
