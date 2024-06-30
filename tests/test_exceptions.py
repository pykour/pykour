from http import HTTPStatus

from pykour.exceptions import HTTPException, ResourceNotFoundException


def test_http_exception_with_default_message():
    exception = HTTPException(HTTPStatus.BAD_REQUEST)
    assert str(exception) == "400: Bad Request"
    assert repr(exception) == "HTTPException(status_code=400 message=Bad Request)"


def test_http_exception_with_custom_message():
    exception = HTTPException(HTTPStatus.BAD_REQUEST, "Custom message")
    assert str(exception) == "400: Custom message"
    assert repr(exception) == "HTTPException(status_code=400 message=Custom message)"


def test_resource_not_found_exception_with_default_message():
    exception = ResourceNotFoundException()
    assert str(exception) == "404: Not Found"
    assert repr(exception) == "ResourceNotFoundException(status_code=404 message=Not Found)"


def test_resource_not_found_exception_with_custom_message():
    exception = ResourceNotFoundException("Resource not found")
    assert str(exception) == "404: Resource not found"
    assert repr(exception) == "ResourceNotFoundException(status_code=404 message=Resource not found)"
