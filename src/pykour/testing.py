from __future__ import annotations
from unittest.mock import AsyncMock

from pykour.types import Scope
from pykour import __version__, Pykour


class Assertion:
    def __init__(self, scope: Scope, receive: AsyncMock, send: AsyncMock):
        self.scope = scope
        self.receive = receive
        self.send = send

    def is_ok(self) -> Assertion:
        assert self.get_status_code() == 200
        return self

    def is_not_found(self) -> Assertion:
        assert self.get_status_code() == 404
        return self

    def is_server_error(self) -> Assertion:
        assert self.get_status_code() == 500
        return self

    def is_bad_request(self) -> Assertion:
        assert self.get_status_code() == 400
        return self

    def is_method_not_allowed(self) -> Assertion:
        assert self.get_status_code() == 405
        return self

    def expect(self, body: str) -> Assertion:
        assert self.get_body() == body
        return self

    def get_status_code(self) -> int:
        call_args_list = self.send.call_args_list
        for call_args in call_args_list:
            if call_args[0][0]["type"] == "http.response.start":
                return call_args[0][0]["status"]
        return 0

    def get_body(self) -> str:
        call_args_list = self.send.call_args_list
        for call_args in call_args_list:
            if call_args[0][0]["type"] == "http.response.body":
                return call_args[0][0]["body"].decode()
        return ""


def get(url: str) -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
        ],
    }


def post(url: str, body: str) -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
            [b"content-length", str(len(body)).encode()],
        ],
        "body": body.encode(),
    }


def put(url: str, body: str) -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": "http",
        "http_version": "1.1",
        "method": "PUT",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
            [b"content-length", str(len(body)).encode()],
        ],
        "body": body.encode(),
    }


def delete(url: str) -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": "http",
        "http_version": "1.1",
        "method": "DELETE",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
        ],
    }


def patch(url: str, body: str) -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": "http",
        "http_version": "1.1",
        "method": "PATCH",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
            [b"content-length", str(len(body)).encode()],
        ],
        "body": body.encode(),
    }


def head(url: str) -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": "http",
        "http_version": "1.1",
        "method": "HEAD",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
        ],
    }


def scope(url: str, scheme: str = "http", method: str = "GET", body: str = ""):
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": scheme,
        "http_version": "1.1",
        "method": method,
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
            [b"content-length", str(len(body)).encode()],
        ],
        "body": body.encode(),
    }


async def perform(app: Pykour, scope: Scope) -> Assertion:
    receive = AsyncMock()
    send = AsyncMock()
    await app(scope, receive, send)
    return Assertion(scope, receive, send)
