from typing import Union
from http import HTTPStatus


class Response:

    def __init__(
        self,
        send,
        status_code: Union[HTTPStatus, int],
        charset: str = "utf-8",
        content_type: str = "application/json",
    ) -> None:
        self.send = send
        self._status_code = status_code
        self._charset = charset
        self._content_type = content_type
        self._headers = []
        self._headers.append(("Content-Type", f"{content_type}; charset={charset}"))
        self._content = ""

    @property
    def status(self) -> Union[HTTPStatus, int]:
        return self._status_code

    @status.setter
    def status(self, status_code: Union[HTTPStatus, int]) -> None:
        self._status_code = status_code

    @property
    def charset(self) -> str:
        return self._charset

    @charset.setter
    def charset(self, charset: str) -> None:
        self._charset = charset
        self._headers[0] = ("Content-Type", f"{self._content_type}; charset={charset}")

    @property
    def content_type(self) -> str:
        return self._content_type

    @content_type.setter
    def content_type(self, content_type: str) -> None:
        self._content_type = content_type
        self._headers[0] = ("Content-Type", f"{content_type}; charset={self._charset}")

    @property
    def headers(self) -> list[tuple[str, str]]:
        return self._headers

    def get_header(self, key: str) -> list[str]:
        result = []
        for header in self._headers:
            if header[0] == key:
                result.append(header[1])
        return result

    def add_header(self, key: str, value: str) -> None:
        self._headers.append((key, value))

    @property
    def content(self) -> str:
        return self._content

    @content.setter
    def content(self, content: str) -> None:
        self._content = content

    async def render(self) -> None:
        await self.send(
            {
                "type": "http.response.start",
                "status": self._status_code,
                "headers": self._headers,
            }
        )
        await self.send({"type": "http.response.body", "body": self._content.encode(self._charset)})
