from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

from pykour.types import Scope
from pykour import __version__, Pykour


class Assertion:
    def __init__(self, scope: Scope, receive: AsyncMock, send: AsyncMock):
        self.scope = scope
        self.receive = receive
        self.send = send

    def is_ok(self) -> Assertion:
        assert self.get_status_code() == 200, f"Expected 200, but got {self.get_status_code()}"
        return self

    def is_created(self) -> Assertion:
        assert self.get_status_code() == 201, f"Expected 201, but got {self.get_status_code()}"
        return self

    def is_no_content(self) -> Assertion:
        assert self.get_status_code() == 204, f"Expected 204, but got {self.get_status_code()}"
        return self

    def is_not_found(self) -> Assertion:
        assert self.get_status_code() == 404, f"Expected 404, but got {self.get_status_code()}"
        return self

    def is_bad_request(self) -> Assertion:
        assert self.get_status_code() == 400, f"Expected 400, but got {self.get_status_code()}"
        return self

    def is_method_not_allowed(self) -> Assertion:
        assert self.get_status_code() == 405, f"Expected 405, but got {self.get_status_code()}"
        return self

    def is_internal_server_error(self) -> Assertion:
        assert self.get_status_code() == 500, f"Expected 500, but got {self.get_status_code()}"
        return self

    def expect(self, expected: Any) -> Assertion:
        actual = self.get_body()
        if isinstance(expected, dict):
            actual = json.loads(self.get_body())
        assert actual == expected, f"Expected '{expected}', but got '{actual}'"
        return self

    def empty(self) -> Assertion:
        assert self.get_body() == "", f"Expected empty body, but got '{self.get_body()}'"
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


def get(url: str, scheme: str = "http", version: str = "1.1") -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": scheme,
        "http_version": version,
        "method": "GET",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
        ],
    }


def post(url: str, body: str = "", scheme: str = "http", version: str = "1.1") -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": scheme,
        "http_version": version,
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


def put(url: str, body: str = "", scheme: str = "http", version: str = "1.1") -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": scheme,
        "http_version": version,
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


def delete(url: str, scheme: str = "http", version: str = "1.1") -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": scheme,
        "http_version": version,
        "method": "DELETE",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
        ],
    }


def patch(url: str, body: str = "", scheme: str = "http", version: str = "1.1") -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": scheme,
        "http_version": version,
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


def head(url: str, scheme: str = "http", version: str = "1.1") -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": scheme,
        "http_version": version,
        "method": "HEAD",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
        ],
    }


def trace(url: str, scheme: str = "http", version: str = "1.1") -> Scope:
    url_split = url.split("?")

    return {
        "type": "http",
        "scheme": scheme,
        "http_version": version,
        "method": "TRACE",
        "path": url_split[0],
        "query_string": url_split[1].encode() if len(url_split) > 1 else b"",
        "headers": [
            [b"host", b"localhost:8000"],
            [b"user-agent", f"pykour/{__version__}".encode()],
            [b"accept", b"*/*"],
        ],
    }


async def perform(app: Pykour, scope: Scope) -> Assertion:
    receive = AsyncMock()
    send = AsyncMock()
    await app(scope, receive, send)
    return Assertion(scope, receive, send)