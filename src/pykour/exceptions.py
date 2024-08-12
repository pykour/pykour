from __future__ import annotations

from http import HTTPStatus
from typing import Union


class HTTPException(Exception):
    """HTTPException is a base class for HTTP exceptions."""

    def __init__(self, status_code: int, message: Union[str, None] = None) -> None:
        if message is None:
            message = HTTPStatus(status_code).phrase
        self.status_code = status_code
        self.message = str(message)

    def __str__(self) -> str:
        return f"{self.status_code} {self.message}"

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code} message={self.message})"


class ResourceNotFoundException(HTTPException):
    """ResourceNotFoundException is raised when a resource is not found."""

    def __init__(self, message: Union[str, None] = None) -> None:
        super().__init__(status_code=HTTPStatus.NOT_FOUND, message=message)


class ValidationError(ValueError):
    """ValidationError is raised when a value is not valid."""

    def __init__(self, message: Union[str, None] = None, caused_by: Exception = None) -> None:
        if message is None:
            self.message = "Validation error"
        else:
            self.message = str(message)
        self.caused_by = caused_by

    def __str__(self) -> str:
        if self.caused_by:
            return f"{self.message or ''} caused by {self.caused_by}"
        else:
            return self.message or ""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r})"


class DatabaseOperationError(Exception):
    """DatabaseOperationError is raised when a database operation fails."""

    def __init__(self, message: Union[str, None] = None, caused_by: Exception = None) -> None:
        if message is None:
            self.message = "Database operation error"
        else:
            self.message = str(message)
        self.caused_by = caused_by

    def __str__(self) -> str:
        if self.caused_by:
            return f"{self.message or ''} caused by {self.caused_by}"
        else:
            return self.message or ""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r})"
