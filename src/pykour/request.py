import json
from typing import Mapping, Any, Iterator, cast, List, Tuple, Union
from collections import defaultdict

from pykour.types import Scope, Receive
from pykour.url import URL
from urllib.parse import parse_qs


class Request(Mapping[str, Any]):
    """Request is a class that represents a request from a client."""

    def __init__(self, scope: Scope, receive: Receive):
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
        self.path_params: dict[str, str] = {}

        if "headers" in self.scope:
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
    def app(self) -> Any:
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
    def method(self) -> Union[str, None]:
        """Returns the HTTP method.

        Returns:
            HTTP method.
        """
        if "method" not in self.scope:
            return None
        else:
            return cast(str, self.scope["method"])

    @property
    def scheme(self) -> Union[str, None]:
        """Returns the URL scheme."""

        if "scheme" not in self.scope:
            return None
        else:
            return cast(str, self.scope["scheme"]).upper()

    @property
    def version(self) -> Union[str, None]:
        """Returns the HTTP version.

        Returns:
            HTTP version.
        """
        if "http_version" not in self.scope:
            return None
        else:
            return self.scope["http_version"]

    @property
    def client(self) -> Union[str, None]:
        """Returns the client address.

        Returns:
            Client address.
        """
        if "client" not in self.scope:
            return None
        else:
            client = self.scope["client"]
            return f"{client[0]}:{client[1]}"

    @property
    def path(self) -> str:
        """Returns the request path.

        Returns:
            Request path.
        """
        return self.scope["path"]

    @property
    def query_string(self) -> str:
        """Returns the query string.

        Returns:
            Query string.
        """
        return self.scope["query_string"]

    @property
    def query_params(self) -> dict[str, Union[str, list[str]]]:
        """Returns the query parameters.

        Returns:
            Query parameters.
        """
        query_string = self.scope["query_string"].decode("utf-8")

        parsed_dict = parse_qs(query_string)

        result = {k: (v[0] if len(v) == 1 else v) for k, v in parsed_dict.items()}
        return result

    @property
    def accept(self) -> List[str]:
        """Returns the accept header.

        Returns:
            Accept header.
        """
        return self.get_sorted_accept_list(self.scope)

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

    @staticmethod
    def parse_accept_header(accept_header: str) -> List[Tuple[str, float]]:
        """
        Parse the accept header and return a sorted list of MIME types.
        """
        accept_values = accept_header.split(",")
        result = []

        for value in accept_values:
            parts = value.split(";")
            mime_type = parts[0].strip()
            q_value = 1.0

            if len(parts) > 1 and parts[1].strip().startswith("q="):
                try:
                    q_value = float(parts[1].strip()[2:])
                except ValueError:
                    pass

            result.append((mime_type, q_value))

        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def get_sorted_accept_list(self, scope: Scope) -> List[str]:
        """
        Parse the accept header and return a sorted list of MIME types.
        """
        headers = scope.get("headers", [])
        accept_header = ""

        for header in headers:
            if header[0].decode("latin-1") == "accept":
                accept_header = header[1].decode("latin-1")
                break

        if not accept_header:
            return []

        parsed_accept = self.parse_accept_header(accept_header)
        return [mime_type for mime_type, q_value in parsed_accept]
