import pytest

from pykour.schema import BaseSchema
from pykour.validator import validate


class TestSchema1(BaseSchema):
    name: str
    age: int


class TestSubSchema(BaseSchema):
    value: int


class TestDto:
    value: int


class TestSchema2(BaseSchema):
    value1: dict[str, str]
    value2: list[int]
    value3: TestSubSchema
    value4: TestDto


class TestSchema3(BaseSchema):
    value1: int
    value2: str
    value3: str

    @validate("value1")
    def validate_value1(self, value: str) -> None:
        if value is None:
            return
        if int(value) >= 0:
            raise ValueError("key not found in value1")


def test_should_initialize_with_valid_data():
    data = {"name": "John Doe", "age": 30}
    schema = TestSchema1.from_dict(data)
    assert schema.name == "John Doe"
    assert schema.age == 30


def test_should_handle_missing_optional_fields():
    data = {"name": "John Doe"}
    schema = TestSchema1.from_dict(data)
    assert schema.name == "John Doe"
    assert schema.age is None


def test_should_handle_nested_schemas():
    data = {"value1": {"key": "value"}, "value2": [1, 2, 3], "value3": {"value": 42}, "value4": {"value": 42}}
    schema = TestSchema2.from_dict(data)
    assert schema.value1 == {"key": "value"}
    assert schema.value2 == [1, 2, 3]


def test_should_handle_validation():
    data = {"value1": 42}
    with pytest.raises(ValueError) as exc:
        TestSchema3.from_dict(data)
