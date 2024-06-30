from pykour.request import Request


def test_create_request():
    scope = {
        "app": "test",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [(b"host", b"example.com")],
    }
    request = Request(scope, None)
    assert request.app == "test"
    assert request.method == "GET"
    assert request.url.scheme == "http"
    assert request.url.netloc == "example.com"
    assert request.url.path == "/test"
    assert request.url.query == ""
    assert request.url.fragment == ""
