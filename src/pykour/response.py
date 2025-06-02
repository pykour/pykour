import json
from typing import Any

from .headers import Headers
from .types import Send


class Response:
    def __init__(
        self,
        body: bytes | str | dict[str, Any] | None = None,
        status: int | None = None,
        headers: dict[str, str] | Headers | None = None,
        method: str | None = None,
    ) -> None:
        # Set default status based on method if not provided
        if status is None:
            if method == "POST":
                self.status = 201
            elif method == "DELETE":
                self.status = 204
            else:
                self.status = 200
        else:
            self.status = status
        self._body = body
        self._headers = Headers([]) if headers is None else self._prepare_headers(headers)

    def _prepare_headers(self, headers: dict[str, str] | Headers) -> Headers:
        if isinstance(headers, Headers):
            return headers.copy()
        else:
            h = Headers([])
            h.update(headers)
            return h

    def _prepare_body(self) -> bytes:
        if self._body is None:
            return b""
        elif isinstance(self._body, bytes):
            return self._body
        elif isinstance(self._body, str):
            if "content-type" not in self._headers:
                self._headers["content-type"] = "text/plain; charset=utf-8"
            return self._body.encode("utf-8")
        elif isinstance(self._body, dict):
            if "content-type" not in self._headers:
                self._headers["content-type"] = "application/json"
            return json.dumps(self._body).encode("utf-8")
        else:
            raise TypeError(f"Unsupported body type: {type(self._body)}")

    async def send(self, send: Send) -> None:
        body = self._prepare_body()

        if body and "content-length" not in self._headers:
            self._headers["content-length"] = str(len(body))

        await send({
            "type": "http.response.start",
            "status": self.status,
            "headers": self._headers.as_list(),
        })

        await send({
            "type": "http.response.body",
            "body": body,
        })