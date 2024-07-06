from pykour.url import URL


def test_url_creation_with_scope_without_host_header():
    scope = {
        "scheme": "http",
        "server": ("localhost", 8000),
        "path": "/home",
        "query_string": b"param=value",
        "headers": [(b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "http://localhost:8000/home?param=value"


def test_url_creation_with_scope_with_host_header():
    scope = {
        "scheme": "http",
        "server": ("localhost", 8000),
        "path": "/home",
        "query_string": b"param=value",
        "headers": [(b"host", b"example.com"), (b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "http://example.com/home?param=value"


def test_url_creation_with_scope_without_server():
    scope = {
        "scheme": "http",
        "path": "/home",
        "query_string": b"param=value",
        "headers": [(b"host", b"example.com"), (b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "http://example.com/home?param=value"


def test_url_creation_with_scope_without_server_without_host_header():
    scope = {
        "scheme": "http",
        "path": "/home",
        "query_string": b"param=value",
        "headers": [(b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "/home?param=value"


def test_url_creation_with_scope_with_default_port():
    scope = {
        "scheme": "http",
        "server": ("localhost", 80),
        "path": "/home",
        "query_string": b"param=value",
        "headers": [(b"host", b"example.com"), (b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "http://example.com/home?param=value"


def test_url_creation_with_scope_with_default_port_without_host_header():
    scope = {
        "scheme": "http",
        "server": ("localhost", 80),
        "path": "/home",
        "query_string": b"param=value",
        "headers": [(b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "http://localhost/home?param=value"


def test_url_creation_with_scope_without_query_string():
    scope = {
        "scheme": "http",
        "server": ("localhost", 8000),
        "path": "/home",
        "headers": [(b"content-type", b"text/html")],
    }
    url = URL(scope=scope)
    assert str(url) == "http://localhost:8000/home"


def test_url_components():
    url = URL("https://username:password@hostname:8080/path?query=param#fragment")
    assert url.scheme == "https"
    assert url.netloc == "username:password@hostname:8080"
    assert url.path == "/path"
    assert url.query == "query=param"
    assert url.fragment == "fragment"
    assert url.username == "username"
    assert url.password == "password"
    assert url.hostname == "hostname"
    assert url.port == 8080


def test_url_is_secure():
    url = URL("https://hostname")
    assert url.is_secure is True

    url = URL("http://hostname")
    assert url.is_secure is False


def test_url_query_params():
    url = URL("http://hostname/path?param1=value1&param2=value2")
    assert url.query_params == {"param1": "value1", "param2": "value2"}


def test_url_normalize():
    url = URL("HTTP://HOSTNAME:80/Path?Param2=Value2&Param1=Value1#Fragment")
    normalized_url = url.normalize()
    assert normalized_url.scheme == "http"
    assert normalized_url.netloc == "hostname:80"
    assert normalized_url.path == "/Path"
    assert normalized_url.query == "Param1=Value1&Param2=Value2"
    assert normalized_url.fragment == "Fragment"


def test_url_replace():
    url = URL("http://hostname/path")
    replaced_url = url.replace(
        scheme="https",
        netloc="username:password@newhostname:8080",
        path="/newpath",
        query="newquery=newvalue",
        fragment="newfragment",
    )
    assert replaced_url.scheme == "https"
    assert replaced_url.netloc == "username:password@newhostname:8080"
    assert replaced_url.path == "/newpath"
    assert replaced_url.query == "newquery=newvalue"
    assert replaced_url.fragment == "newfragment"


def test_url_replace_with_port():
    url = URL("http://hostname/path")
    replaced_url = url.replace(
        port=8080,
    )
    assert replaced_url.scheme == "http"
    assert replaced_url.hostname == "hostname"
    assert replaced_url.port == 8080
    assert replaced_url.path == "/path"


def test_url_equality():
    url1 = URL("http://hostname/path")
    url2 = URL("http://hostname/path")
    assert url1 == url2

    url2 = URL("http://hostname/differentpath")
    assert url1 != url2


def test_url_string_representation():
    url = URL("http://username:password@hostname/path")
    assert str(url) == "http://username:password@hostname/path"


def test_url_repr_without_password():
    url = URL("http://username:password@hostname/path")
    assert repr(url) == "URL('http://username:********@hostname/path')"


def test_url_repr_with_password():
    url = URL("http://username@hostname/path")
    assert repr(url) == "URL('http://username@hostname/path')"
