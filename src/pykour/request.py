import typing
from urllib.parse import parse_qs, unquote

from .types import Scope, Receive
from .headers import Headers


class Request:
    def __init__(self, scope: Scope, receive: Receive):
        self._scope = scope
        self._receive = receive
        self._request: dict[str, typing.Any] = {}
        self._headers: Headers | None = None
        self._body: bytes | None = None
        self._query_params: dict[str, list[str]] | None = None

    @property
    def method(self) -> str:
        return self._scope["method"]

    @property
    def path(self) -> str:
        return self._scope["path"]

    @property
    def raw_path(self) -> bytes:
        return self._scope.get("raw_path", self.path.encode("utf-8"))

    @property
    def root_path(self) -> str:
        return self._scope.get("root_path", "")

    @property
    def scheme(self) -> str:
        return self._scope.get("scheme", "http")

    @property
    def query_string(self) -> bytes:
        return self._scope.get("query_string", b"")

    @property
    def query_params(self) -> dict[str, list[str]]:
        if self._query_params is None:
            self._query_params = parse_qs(self.query_string.decode("utf-8"))
        return self._query_params

    @property
    def headers(self) -> Headers:
        if self._headers is None:
            raw_headers = self._scope.get("headers", [])
            self._headers = Headers(raw_headers)
        return self._headers

    @property
    def server(self) -> tuple[str, int] | None:
        return self._scope.get("server")

    @property
    def client(self) -> tuple[str, int] | None:
        return self._scope.get("client")

    @property
    def asgi(self) -> dict[str, typing.Any]:
        return self._scope.get("asgi", {})

    @property
    def http_version(self) -> str:
        return self._scope.get("http_version", "1.1")

    @property
    def url(self) -> str:
        host = self.headers.get_first("host", "localhost")
        return f"{self.scheme}://{host}{self.path}"

    @property
    def full_url(self) -> str:
        url = self.url
        if self.query_string:
            url += f"?{self.query_string.decode('utf-8')}"
        return url

    async def body(self) -> bytes:
        if self._body is None:
            body = b""
            while True:
                message = await self._receive()
                body += message.get("body", b"")
                if not message.get("more_body", False):
                    break
            self._body = body
        return self._body

    async def json(self) -> typing.Any:
        import json
        body = await self.body()
        return json.loads(body.decode("utf-8"))

    async def form(self) -> dict[str, str | list[str]]:
        body = await self.body()
        content_type = self.headers.get_first("content-type", "")
        
        if "application/x-www-form-urlencoded" in content_type:
            form_data = parse_qs(body.decode("utf-8"))
            return {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}
        
        return {}

    def get(self, key: str, default: str | None = None) -> str | None:
        try:
            return getattr(self, key)
        except AttributeError:
            if key in self._request:
                value = self._request[key]
                setattr(self, key, value)
                return value
            return default

    def copy(self) -> typing.Self:
        new = type(self)(self._scope, self._receive)
        new._request = self._request.copy()
        new._headers = self._headers.copy() if self._headers else None
        return new

    def keys(self) -> list[str]:
        return list(self._request.keys())

    def values(self) -> list[typing.Any]:
        return [self[k] for k in self.keys()]

    def items(self) -> list[tuple[str, typing.Any]]:
        return [(k, self[k]) for k in self.keys()]

    def __getitem__(self, key: str) -> typing.Any:
        try:
            return getattr(self, key)
        except AttributeError:
            try:
                value = self._request[key]
                setattr(self, key, value)
                return value
            except KeyError:
                raise KeyError(f"Key '{key}' not found in request scope.")

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key) or key in self._request

    def __iter__(self) -> typing.Iterator[str]:
        attr_keys = (k for k in self.__dict__ if not k.startswith("_"))
        request_keys = self._request.keys()
        return iter(set(attr_keys) | set(request_keys))

    def __len__(self) -> int:
        return len(self._request)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Request):
            return NotImplemented
        if set(self._request.keys()) != set(other._request.keys()):
            return False
        for key in self._request:
            if self._request[key] != other._request.get(key):
                return False
        return True

    def __bool__(self) -> bool:
        return bool(self._request)

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} {self._request!r}>"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._request!r})"
