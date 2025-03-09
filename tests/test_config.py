import pytest

from pykour.config import Config


@pytest.mark.it("should set and get value using key")
def test_set_get_value():
    config = Config()
    config["key1"] = "value1"
    config["key2"] = "value2"
    assert config["key1"] == "value1"
    assert config["key2"] == "value2"
