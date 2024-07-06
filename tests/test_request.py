from pykour.request import Request


def test_create_request():
    scope = {
        "http_version": "1.1",
        "app": "test",
        "method": "GET",
        "path": "/test",
        "query_string": b"a",
        "headers": [(b"host", b"example.com")],
    }
    request = Request(scope, None)
    assert request.version == "1.1"
    assert request.app == "test"
    assert request.method == "GET"
    assert request.query_string == b"a"
    assert request.get_header("host") == ["example.com"]
    assert request.url.scheme == "http"
    assert request.url.netloc == "example.com"
    assert request.url.path == "/test"
    assert request.url.query == "a"
    assert request.url.fragment == ""
    assert len(request) == 6
    assert request["http_version"] == "1.1"
    for key, value in request.items():
        assert request[key] == value
