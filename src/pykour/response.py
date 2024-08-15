from http import HTTPStatus

from pykour.types import Send, HTTPStatusCode


class Response:
    """Response is a class that represents an HTTP response."""

    def __init__(
        self,
        send: Send,
        status_code: HTTPStatusCode = HTTPStatus.OK,
        charset: str = "utf-8",
        content_type: str = "application/json",
    ) -> None:
        """Create a new Response object.

        Args:
            send: The send function of the ASGI application.
            status_code: The status code of the response.
            charset: The charset of the response.
            content_type: The content type of the response.
        """

        self.send = send
        self._status_code = status_code
        self._charset = charset
        self._content_type = content_type
        self._headers = []
        self._headers.append((b"Content-Type", f"{content_type}; charset={charset}".encode("latin-1")))
        self._content = ""

    @property
    def status(self) -> HTTPStatusCode:
        """Get the status code of the response.

        Returns:
            The status code of the response.
        """
        return self._status_code

    @status.setter
    def status(self, status_code: HTTPStatusCode) -> None:
        """Set the status code of the response.

        Args:
            status_code: The status code of the response.
        """

        self._status_code = status_code

    @property
    def charset(self) -> str:
        """Get the charset of the response.

        Returns:
            The charset of the response.
        """
        return self._charset

    @charset.setter
    def charset(self, charset: str) -> None:
        """Set the charset of the response.

        Args:
            charset: The charset of the response.
        """
        self._charset = charset
        self._headers[0] = (b"Content-Type", f"{self._content_type}; charset={charset}".encode("latin-1"))

    @property
    def content_type(self) -> str:
        """Get the content type of the response.

        Returns:
            The content type of the response.
        """

        return self._content_type

    @content_type.setter
    def content_type(self, content_type: str) -> None:
        """Set the content type of the response.

        Args:
            content_type: The content type of the response.
        """

        self._content_type = content_type
        self._headers[0] = (b"Content-Type", f"{content_type}; charset={self._charset}".encode("latin-1"))

    @property
    def headers(self) -> list[tuple[str, str]]:
        """Get the headers of the response.

        Returns:
            The headers of the response.
        """
        return list(map(lambda header: (header[0].decode("latin-1"), header[1].decode("latin-1")), self._headers))

    def get_header(self, key: str) -> list[str]:
        """Get the value of a header.

        Args:
            key: The key of the header.
        """

        result = []
        for header in self._headers:
            if header[0] == key.encode("latin-1"):
                result.append(header[1].decode("latin-1"))
        return result

    def add_header(self, key: str, value: str) -> None:
        """Add a header to the response.

        Args:
            key: The key of the header.
            value: The value of the header.
        """
        self._headers.append((key.encode("latin-1"), value.encode("latin-1")))

    @property
    def content(self) -> str:
        """Get the content of the response.

        Returns:
            The content of the response.
        """
        return self._content

    @content.setter
    def content(self, content: str) -> None:
        """Set the content of the response.

        Args:
            content: The content of the response.
        """
        self._content = content

    async def render(self) -> None:
        """Render the response."""

        await self.send(
            {
                "type": "http.response.start",
                "status": self._status_code,
                "headers": self._headers,
            }
        )
        if self._status_code == HTTPStatus.NO_CONTENT or self.content is None or self.content == "":
            await self.send({"type": "http.response.body", "body": b""})
        else:
            await self.send({"type": "http.response.body", "body": self._content.encode(self._charset)})
