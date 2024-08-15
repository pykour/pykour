from http import HTTPStatus
from unittest.mock import AsyncMock

import pytest

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


def test_set_charset_using_setter():
    response = Response(None, status_code=200)
    response.charset = "latin-1"
    assert response.charset == "latin-1"


def test_set_content_type():
    response = Response(None, status_code=200)
    assert response.content_type == "application/json"


def test_set_content_type_using_setter():
    response = Response(None, status_code=200)
    response.content_type = "text/html"
    assert response.content_type == "text/html"


def test_add_header():
    response = Response(None, status_code=200)
    response.add_header("Content-Type", "text/html")
    assert response.headers == [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Type", "text/html"),
    ]
    assert response.get_header("Content-Type") == ["application/json; charset=utf-8", "text/html"]


def test_add_header_new_key():
    response = Response(None, status_code=200)
    response.add_header("Content-Length", "42")
    assert response.headers == [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", "42"),
    ]


def test_content():
    response = Response(None, status_code=200)
    response.content = "Hello, World!"
    assert response.content == "Hello, World!"
    assert response.headers == [
        ("Content-Type", "application/json; charset=utf-8"),
    ]


@pytest.mark.asyncio
async def test_render_no_content():
    send_mock = AsyncMock()
    response = Response(send=send_mock, status_code=HTTPStatus.NO_CONTENT)
    await response.render()

    send_mock.assert_any_await(
        {
            "type": "http.response.start",
            "status": HTTPStatus.NO_CONTENT,
            "headers": [(b"Content-Type", b"application/json; charset=utf-8")],
        }
    )
    send_mock.assert_any_await({"type": "http.response.body", "body": b""})


@pytest.mark.asyncio
async def test_render_with_content():
    send_mock = AsyncMock()
    response = Response(send=send_mock, status_code=HTTPStatus.OK)
    response._content = "Hello, world!"
    await response.render()

    send_mock.assert_any_await(
        {
            "type": "http.response.start",
            "status": HTTPStatus.OK,
            "headers": [(b"Content-Type", b"application/json; charset=utf-8")],
        }
    )
    send_mock.assert_any_await({"type": "http.response.body", "body": b"Hello, world!"})


@pytest.mark.asyncio
async def test_render_empty_content():
    send_mock = AsyncMock()
    response = Response(send=send_mock, status_code=HTTPStatus.OK)
    response._content = ""
    await response.render()

    send_mock.assert_any_await(
        {
            "type": "http.response.start",
            "status": HTTPStatus.OK,
            "headers": [(b"Content-Type", b"application/json; charset=utf-8")],
        }
    )
    send_mock.assert_any_await({"type": "http.response.body", "body": b""})


@pytest.mark.asyncio
async def test_render_none_content():
    send_mock = AsyncMock()
    response = Response(send=send_mock, status_code=HTTPStatus.OK)
    response._content = None
    await response.render()

    send_mock.assert_any_await(
        {
            "type": "http.response.start",
            "status": HTTPStatus.OK,
            "headers": [(b"Content-Type", b"application/json; charset=utf-8")],
        }
    )
    send_mock.assert_any_await({"type": "http.response.body", "body": b""})
