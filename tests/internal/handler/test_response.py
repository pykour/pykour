from http import HTTPStatus
from unittest.mock import MagicMock

import pytest


def test_determine_content_type_for_response_body():
    from pykour.internal.handler.response import determine_content_type_for_response_body
    from pykour.request import Request

    request = MagicMock(spec=Request)

    request.accept = ["text/plain"]
    assert determine_content_type_for_response_body(request, "") == "text/plain"

    request.accept = ["application/json"]
    assert determine_content_type_for_response_body(request, "") == "application/json"

    request.accept = ["*/*"]
    assert determine_content_type_for_response_body(request, "") == "text/plain"
    assert determine_content_type_for_response_body(request, {}) == "application/json"

    request.accept = ["text/html"]
    assert determine_content_type_for_response_body(request, "") == "text/plain"


def test_determine_content_type_for_error_response():
    from pykour.internal.handler.response import determine_content_type_for_error_response
    from pykour.request import Request

    request = MagicMock(spec=Request)

    request.accept = ["application/json"]
    assert determine_content_type_for_error_response(request) == "application/json"

    request.accept = ["text/plain"]
    assert determine_content_type_for_error_response(request) == "text/plain"

    request.accept = ["text/html"]
    assert determine_content_type_for_error_response(request) == "text/plain"


def test_detect_error_phrase():
    from pykour.internal.handler.response import detect_error_phrase
    from pykour.response import Response

    response = MagicMock(spec=Response)

    response.content_type = "application/json"
    assert detect_error_phrase(response, "error message") == '{"error": "error message"}'

    response.content_type = "text/plain"
    assert detect_error_phrase(response, "error message") == "error message"

    response.content_type = "text/html"
    assert detect_error_phrase(response, "error message") == "error message"


def test_detect_response_body_by_no_content():
    from pykour.internal.handler.response import detect_response_body
    from pykour.request import Request
    from pykour.response import Response

    request = MagicMock(spec=Request)
    response = MagicMock(spec=Response)

    request.method = "DELETE"
    response.status = HTTPStatus.NO_CONTENT
    response.content_type = "application/json"
    detect_response_body(request, response, "response body")
    assert response.content == ""


def test_detect_response_body_by_options_method():
    from pykour.internal.handler.response import detect_response_body
    from pykour.request import Request
    from pykour.response import Response

    app = MagicMock()
    app.get_allowed_methods.return_value = ["GET", "POST", "PUT", "DELETE"]

    request = MagicMock(spec=Request)
    request.app = app
    response = MagicMock(spec=Response)

    request.method = "OPTIONS"
    response.status = HTTPStatus.OK
    response.content_type = "application/json"
    detect_response_body(request, response, "response body")
    assert response.content == ""
    response.add_header.assert_called_once_with("Allow", "GET, POST, PUT, DELETE")


def test_detect_response_body_by_head_method():
    from pykour.internal.handler.response import detect_response_body
    from pykour.request import Request
    from pykour.response import Response

    app = MagicMock()
    app.get_allowed_methods.return_value = ["GET", "POST", "PUT", "DELETE"]

    request = MagicMock(spec=Request)
    request.app = app
    response = MagicMock(spec=Response)

    request.method = "HEAD"
    response.status = HTTPStatus.OK
    response.content_type = "application/json"
    detect_response_body(request, response, "response body")
    assert response.content == ""
    response.add_header.assert_called_once_with("Content-Length", "13")


def test_detect_response_body_by_content_type():
    from pykour.internal.handler.response import detect_response_body
    from pykour.request import Request
    from pykour.response import Response

    request = MagicMock(spec=Request)
    response = MagicMock(spec=Response)

    request.method = "GET"
    response.status = HTTPStatus.OK
    response.content_type = "application/json"
    detect_response_body(request, response, {"key": "value"})
    assert response.content == '{"key": "value"}'

    request.method = "GET"
    response.status = HTTPStatus.OK
    response.content_type = "text/plain"
    detect_response_body(request, response, "response body")
    assert response.content == "response body"

    request.method = "GET"
    response.status = HTTPStatus.OK
    response.content_type = "text/html"
    detect_response_body(request, response, "response body")
    assert response.content == "response body"


@pytest.mark.asyncio
async def test_handle_response():
    from pykour.internal.handler.response import handle_response
    from pykour.request import Request
    from pykour.response import Response

    request = MagicMock(spec=Request)
    response = MagicMock(spec=Response)

    response_body = {"key": "value"}

    await handle_response(request, response, response_body)

    response.content_type = "application/json"
    response.content = '{"key": "value"}'
    response.render.assert_called_once()


@pytest.mark.asyncio
async def test_handle_error():
    from pykour.internal.handler.response import handle_error
    from pykour.request import Request
    from pykour.response import Response
    from http import HTTPStatus

    request = MagicMock(spec=Request)
    response = MagicMock(spec=Response)

    await handle_error(request, response, HTTPStatus.NOT_FOUND)

    response.content_type = "text/plain"
    response.status = HTTPStatus.NOT_FOUND
    response.content = "Not Found"
    response.render.assert_called_once()


@pytest.mark.asyncio
async def test_handle_http_exception():
    from pykour.internal.handler.response import handle_http_exception
    from pykour.request import Request
    from pykour.response import Response
    from http import HTTPStatus
    import pykour.exceptions as ex

    request = MagicMock(spec=Request)
    response = MagicMock(spec=Response)
    e = ex.HTTPException(HTTPStatus.NOT_FOUND, "Not Found")

    await handle_http_exception(request, response, e)

    response.content_type = "text/plain"
    response.status = HTTPStatus.NOT_FOUND
    response.content = "Not Found"
    response.render.assert_called_once()
