from http import HTTPStatus


def test_http_exception_without_message():
    from pykour.exceptions import HTTPException

    # Act
    e = HTTPException(HTTPStatus.BAD_REQUEST)

    # Assert
    assert e.status_code == 400
    assert e.message == "Bad Request"
    assert str(e) == "400 Bad Request"
    assert repr(e) == "HTTPException(status_code=400 message=Bad Request)"


def test_http_exception_with_message():
    from pykour.exceptions import HTTPException

    # Act
    e = HTTPException(HTTPStatus.BAD_REQUEST, "Custom message")

    # Assert
    assert e.status_code == 400
    assert e.message == "Custom message"
    assert str(e) == "400 Custom message"
    assert repr(e) == "HTTPException(status_code=400 message=Custom message)"


def test_resource_not_found_exception_without_message():
    from pykour.exceptions import ResourceNotFoundException

    # Act
    e = ResourceNotFoundException()

    # Assert
    assert e.status_code == 404
    assert e.message == "Not Found"
    assert str(e) == "404 Not Found"
    assert repr(e) == "ResourceNotFoundException(status_code=404 message=Not Found)"


def test_resource_not_found_exception_with_custom_message():
    from pykour.exceptions import ResourceNotFoundException

    # Act
    e = ResourceNotFoundException("Custom message")

    # Assert
    assert e.status_code == 404
    assert e.message == "Custom message"
    assert str(e) == "404 Custom message"
    assert repr(e) == "ResourceNotFoundException(status_code=404 message=Custom message)"


def test_validation_error_exception_without_message():
    from pykour.exceptions import ValidationError

    # Act
    e = ValidationError()

    # Assert
    assert e.args == ()
    assert str(e) == "Validation error"
    assert repr(e) == "ValidationError('Validation error')"


def test_validation_error_exception_with_message():
    from pykour.exceptions import ValidationError

    # Act
    e = ValidationError("Custom message")

    # Assert
    assert e.args == ("Custom message",)
    assert str(e) == "Custom message"
    assert repr(e) == "ValidationError('Custom message')"


def test_validation_error_exception_with_caused_by():
    from pykour.exceptions import ValidationError

    # Arrange
    caused_by = ValueError("Caused by error")

    # Act
    e = ValidationError("Custom message", caused_by)

    # Assert
    assert e.args == ("Custom message", caused_by)
    assert str(e) == "Custom message caused by Caused by error"
    assert repr(e) == "ValidationError('Custom message')"
