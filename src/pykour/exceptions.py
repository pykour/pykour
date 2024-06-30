from __future__ import annotations

from http import HTTPStatus


class HTTPException(Exception):
    def __init__(self, status_code: int, message: str | None = None) -> None:
        if message is None:
            message = HTTPStatus(status_code).phrase
        self.status_code = status_code
        self.message = message

    def __str__(self) -> str:
        return f"{self.status_code}: {self.message}"

    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}(status_code={self.status_code} message={self.message})"


class ResourceNotFoundException(HTTPException):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(status_code=HTTPStatus.NOT_FOUND, message=message)
