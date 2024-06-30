from pykour.response import Response


def test_create_response():
    response = Response(None, status_code=200)
    assert response.status == 200
    assert response.charset == "utf-8"
    assert response.content_type == "application/json"
    assert response.headers == [("Content-Type", "application/json; charset=utf-8")]


def test_set_status():
    response = Response(None, status_code=200)
    response.status = 404
    assert response.status == 404


def test_set_charset():
    response = Response(None, status_code=200)
    assert response.charset == "utf-8"


def test_set_content_type():
    response = Response(None, status_code=200)
    assert response.content_type == "application/json"


def test_add_header():
    response = Response(None, status_code=200)
    response.add_header("Content-Type", "text/html")
    assert response.headers == [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Type", "text/html"),
    ]


def test_add_header_new_key():
    response = Response(None, status_code=200)
    response.add_header("Content-Length", "42")
    assert response.headers == [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", "42"),
    ]
