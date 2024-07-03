import json
from typing import MutableMapping, Mapping, Any, Callable, Awaitable, Iterator, cast
from collections import defaultdict

from pykour.url import URL


class Request(Mapping[str, Any]):
    """Request is a class that represents a request from a client."""

    def __init__(self, scope: MutableMapping[str, Any], receive: Callable[[], Awaitable[dict]]):
        """Initializes a new instance of the Request class.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive function.
        """

        self.scope = scope
        self.receive = receive
        self._headers = defaultdict(list)
        self.content_type = None
        self.charset = "utf-8"

        for key, value in self.scope["headers"]:
            decoded_key = key.decode("latin1").lower()
            decoded_value = value.decode("latin1")
            self._headers[decoded_key].append(decoded_value)

            if decoded_key == "content-type":
                self.content_type = decoded_value
                if "charset=" in decoded_value:
                    self.charset = decoded_value.split("charset=")[-1]

        self._stream_consumed = False

    def __getitem__(self, key: str) -> Any:
        return self.scope[key]

    def __iter__(self) -> Iterator[Any]:
        return iter(self.scope)

    def __len__(self) -> int:
        return len(self.scope)

    __eq__ = object.__eq__
    __hash__ = object.__hash__

    @property
    def app(self) -> str:
        """Returns the ASGI application instance.

        Returns:
            Application name.
        """
        return self.scope["app"]

    @property
    def url(self) -> URL:
        """Returns the URL instance.

        Returns:
            URL instance.
        """
        return URL(scope=self.scope)

    @property
    def headers(self) -> dict[str, list[str]]:
        """Returns the headers.

        Returns:
            Headers.
        """
        return self._headers

    def get_header(self, name: str) -> list[str]:
        """Returns the header value.

        Args:
            name: The header name.
        """
        return self._headers.get(name)

    @property
    def method(self) -> str:
        """Returns the HTTP method.

        Returns:
            HTTP method.
        """
        return cast(str, self.scope["method"])

    @property
    def version(self) -> str:
        """Returns the HTTP version.

        Returns:
            HTTP version.
        """
        return self.scope["http_version"]

    @property
    def query_string(self) -> bytes:
        """Returns the query string.

        Returns:
            Query string.
        """
        return self.scope["query_string"]

    async def body(self) -> bytes:
        """Reads the request body.

        Returns:
            The request body.
        """
        try:
            body = b""
            more_body = True

            while more_body:
                message = await self.receive()
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

            return body
        except Exception as e:
            print(f"Error occurred while receiving body: {e}")
            raise e

    async def json(self) -> Any:
        """Parses the request body as JSON.

        Returns:
            The parsed JSON object.
        """
        try:
            body = await self.body()
            return json.loads(body)
        except Exception as e:
            print(f"Error occurred while parsing JSON: {e}")
            raise e
