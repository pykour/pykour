import pytest

from pykour.headers import Headers


@pytest.fixture()
def mock_headers():
    return [
        (b"Content-Type", b"application/json"),
        (b"X-Test", b"foo"),
        (b"X-Test", b"bar"),
    ]


def test_headers_get(mock_headers):
    headers = Headers(mock_headers)
    assert headers.get("Content-Type") == ["application/json"]
    assert headers.get("content-type") == ["application/json"]
    assert headers.get("CONTENT-TYPE") == ["application/json"]
    assert headers.get("X-Test") == ["foo", "bar"]
    assert headers.get("x-test") == ["foo", "bar"]
    assert headers.get("X-TEST") == ["foo", "bar"]
    assert headers.get("Non-Existent") is None


def test_headers_get_first(mock_headers):
    headers = Headers(mock_headers)
    assert headers.get_first("Content-Type") == "application/json"
    assert headers.get_first("content-type") == "application/json"
    assert headers.get_first("CONTENT-TYPE") == "application/json"
    assert headers.get_first("X-Test") == "foo"
    assert headers.get_first("x-test") == "foo"
    assert headers.get_first("X-TEST") == "foo"
    assert headers.get_first("Non-Existent", "default") == "default"
    assert headers.get_first("Non-Existent") is None


def test_headers_add(mock_headers):
    headers = Headers(mock_headers)
    headers.add("X-New1", "new-value")
    assert headers.get("X-New1") == ["new-value"]
    headers.add("X-New2", "New-Value")
    assert headers.get("X-New2") == ["New-Value"]
    headers.add("X-New3", "foo")
    headers.add("X-New3", "bar")
    assert headers.get("X-New3") == ["foo", "bar"]


def test_headers_extend(mock_headers):
    headers = Headers(mock_headers)
    headers.extend("X-Extended1", ["value1", "value2"])
    assert headers.get("X-Extended1") == ["value1", "value2"]
    headers.extend("X-Extended2", ["Value1", "Value2"])
    assert headers.get("X-Extended2") == ["Value1", "Value2"]
    headers.extend("X-Extended3", ["value1", "value2"])
    headers.extend("X-Extended3", ["value3", "value4"])
    assert headers.get("X-Extended3") == ["value1", "value2", "value3", "value4"]
