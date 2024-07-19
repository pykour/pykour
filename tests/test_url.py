from pykour.url import URL


def test_create_url_throw_exception_with_empty_url():
    try:
        URL()
    except ValueError as e:
        assert str(e) == "Either 'url' or 'scope' must be provided."


def test_create_url_with_url_localhost_without_slash():
    url = URL("http://localhost")
    assert str(url) == "http://localhost"
    assert url == "http://localhost"
    assert url.scheme == "http"
    assert url.hostname == "localhost"
    assert url.port == 80
    assert url.path == "/"
    assert url.query == ""
    assert url.is_secure is False
    assert repr(url) == "URL('http://localhost')"


def test_create_url_with_url_localhost_with_slash():
    url = URL("http://localhost/")
    assert str(url) == "http://localhost/"
    assert url == "http://localhost/"
    assert url.scheme == "http"
    assert url.hostname == "localhost"
    assert url.port == 80
    assert url.path == "/"
    assert url.query == ""
    assert url.query_params == {}
    assert url.is_secure is False
    assert repr(url) == "URL('http://localhost/')"


def test_create_url_with_url_loopback_address():
    url = URL("http://127.0.0.1")
    assert str(url) == "http://127.0.0.1"
    assert url == "http://127.0.0.1"
    assert url.scheme == "http"
    assert url.hostname == "127.0.0.1"
    assert url.port == 80
    assert url.path == "/"
    assert url.query == ""
    assert url.query_params == {}
    assert url.is_secure is False
    assert repr(url) == "URL('http://127.0.0.1')"


def test_create_url_with_url_using_not_default_port():
    url = URL("http://localhost:8080")
    assert str(url) == "http://localhost:8080"
    assert url == "http://localhost:8080"
    assert url.scheme == "http"
    assert url.hostname == "localhost"
    assert url.port == 8080
    assert url.path == "/"
    assert url.query == ""
    assert url.query_params == {}
    assert url.is_secure is False
    assert repr(url) == "URL('http://localhost:8080')"


def test_create_url_with_url_with_https():
    url = URL("https://localhost")
    assert str(url) == "https://localhost"
    assert url == "https://localhost"
    assert url.scheme == "https"
    assert url.hostname == "localhost"
    assert url.port == 443
    assert url.path == "/"
    assert url.query == ""
    assert url.query_params == {}
    assert url.is_secure is True
    assert repr(url) == "URL('https://localhost')"


def test_create_url_with_url_https_with_domain_name():
    url = URL("https://www.example.com")
    assert str(url) == "https://www.example.com"
    assert url == "https://www.example.com"
    assert url.scheme == "https"
    assert url.hostname == "www.example.com"
    assert url.port == 443
    assert url.path == "/"
    assert url.query == ""
    assert url.query_params == {}
    assert url.is_secure is True
    assert repr(url) == "URL('https://www.example.com')"


def test_create_url_with_url_with_https_using_not_default_port():
    url = URL("https://localhost:8443")
    assert str(url) == "https://localhost:8443"
    assert url == "https://localhost:8443"
    assert url.scheme == "https"
    assert url.hostname == "localhost"
    assert url.port == 8443
    assert url.path == "/"
    assert url.query == ""
    assert url.query_params == {}
    assert url.is_secure is True
    assert repr(url) == "URL('https://localhost:8443')"


def test_create_url_with_url_with_path():
    url = URL("http://localhost/home")
    assert str(url) == "http://localhost/home"
    assert url == "http://localhost/home"
    assert url.scheme == "http"
    assert url.hostname == "localhost"
    assert url.port == 80
    assert url.path == "/home"
    assert url.query == ""
    assert url.query_params == {}
    assert url.is_secure is False
    assert repr(url) == "URL('http://localhost/home')"


def test_create_url_with_url_with_single_query_param():
    url = URL("http://localhost/?param1=value1")
    assert str(url) == "http://localhost/?param1=value1"
    assert url == "http://localhost/?param1=value1"
    assert url.scheme == "http"
    assert url.hostname == "localhost"
    assert url.port == 80
    assert url.path == "/"
    assert url.query == "param1=value1"
    assert url.query_params == {"param1": "value1"}
    assert url.is_secure is False
    assert repr(url) == "URL('http://localhost/?param1=value1')"


def test_create_url_with_url_with_multiple_query_params():
    url = URL("http://localhost/?param1=value1&param2=value2")
    assert str(url) == "http://localhost/?param1=value1&param2=value2"
    assert url == "http://localhost/?param1=value1&param2=value2"
    assert url.scheme == "http"
    assert url.hostname == "localhost"
    assert url.port == 80
    assert url.path == "/"
    assert url.query == "param1=value1&param2=value2"
    assert url.query_params == {"param1": "value1", "param2": "value2"}
    assert url.is_secure is False
    assert repr(url) == "URL('http://localhost/?param1=value1&param2=value2')"


def test_create_url_with_url_with_empty_query_param():
    url = URL("http://localhost/?")
    assert str(url) == "http://localhost/?"
    assert url == "http://localhost/?"
    assert url.scheme == "http"
    assert url.hostname == "localhost"
    assert url.port == 80
    assert url.path == "/"
    assert url.query == ""
    assert url.query_params == {}
    assert url.is_secure is False
    assert repr(url) == "URL('http://localhost/?')"


def test_url_create_with_scope_without_host_header():
    scope = {
        "scheme": "http",
        "server": ("localhost", 8000),
        "path": "",
        "headers": [(b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "http://localhost:8000"
    assert url == "http://localhost:8000"
    assert url.scheme == "http"
    assert url.hostname == "localhost"
    assert url.port == 8000
    assert url.path == "/"
    assert url.query == ""
    assert url.is_secure is False
    assert repr(url) == "URL('http://localhost:8000')"


def test_url_create_with_scope_with_query_param():
    scope = {
        "scheme": "http",
        "server": ("localhost", 8000),
        "path": "",
        "query_string": b"param=value",
        "headers": [(b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "http://localhost:8000?param=value"
    assert url == "http://localhost:8000?param=value"
    assert url.scheme == "http"
    assert url.hostname == "localhost"
    assert url.port == 8000
    assert url.path == "/"
    assert url.query == "param=value"
    assert url.is_secure is False
    assert repr(url) == "URL('http://localhost:8000?param=value')"


def test_url_create_with_scope_with_host_header():
    scope = {
        "scheme": "https",
        "server": ("localhost", 8000),
        "path": "",
        "headers": [(b"host", b"example.com"), (b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "https://example.com"
    assert url == "https://example.com"
    assert url.scheme == "https"
    assert url.hostname == "example.com"
    assert url.port == 443
    assert url.path == "/"
    assert url.query == ""
    assert url.is_secure is True
    assert repr(url) == "URL('https://example.com')"


def test_url_create_with_scope_with_default_port():
    scope = {
        "scheme": "https",
        "server": ("localhost", 443),
        "path": "",
        "headers": [(b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "https://localhost"
    assert url == "https://localhost"
    assert url.scheme == "https"
    assert url.hostname == "localhost"
    assert url.port == 443
    assert url.path == "/"
    assert url.query == ""
    assert url.is_secure is True
    assert repr(url) == "URL('https://localhost')"


def test_url_create_with_scope_without_server():
    scope = {
        "scheme": "https",
        "path": "/home",
        "headers": [(b"content-type", b"text/html")],
    }
    try:
        url = URL(scope=scope)
    except ValueError as e:
        assert str(e) == "Could not determine the URL."
