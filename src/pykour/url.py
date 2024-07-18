from __future__ import annotations

from typing import Any
from urllib.parse import (
    SplitResult,
    parse_qsl,
    urlsplit,
)

from pykour.types import Scope


class URL:
    """URL is a class that represents a URL."""

    def __init__(self, url: str = None, scope: Scope = None) -> None:
        """URL is a class that represents a URL.

        Args:
            url: The URL.
            scope: The ASGI scope.
        """

        if not url and not scope:
            raise ValueError("Either 'url' or 'scope' must be provided.")

        if not url and scope:
            scheme = scope.get("scheme", "http")
            server = scope.get("server", None)
            path = scope["path"]
            query_string = scope.get("query_string", b"")

            host_header = None
            for key, value in scope["headers"]:
                if key == b"host":
                    host_header = value.decode("latin-1")
                    break

            if host_header is not None:
                url = f"{scheme}://{host_header}{path}"
            elif server:
                host, port = server
                default_port = {"http": 80, "https": 443}[scheme]
                if port == default_port:
                    url = f"{scheme}://{host}{path}"
                else:
                    url = f"{scheme}://{host}:{port}{path}"
            else:
                raise ValueError("Could not determine the URL.")

            if query_string:
                url += "?" + query_string.decode()

        self.url = url

    @property
    def components(self) -> SplitResult:
        """Returns the URL components.

        Returns:
            The URL components.
        """
        return urlsplit(self.url)

    @property
    def scheme(self) -> str:
        """Returns the scheme.

        Returns:
            The scheme.
        """
        return self.components.scheme

    @property
    def hostname(self) -> str:
        """Returns the hostname.

        Returns:
            The hostname.
        """
        return self.components.hostname

    @property
    def port(self) -> int:
        """Returns the port number.

        Returns:
            The port number.
        """
        return self.components.port or {"http": 80, "https": 443}[self.scheme]

    @property
    def path(self) -> str:
        """Returns the path.

        Returns:
            The path.
        """
        return self.components.path or "/"

    @property
    def query(self) -> str:
        """Returns the query string.

        Returns:
            The query string.
        """
        return self.components.query

    @property
    def is_secure(self) -> bool:
        """Returns True if the URL is secure.

        Returns:
            True if the URL is secure.
        """
        return self.scheme in ("https", "wss")

    @property
    def query_params(self) -> dict:
        return dict(parse_qsl(self.query))

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __str__(self) -> str:
        return self.url

    def __repr__(self) -> str:
        url = str(self)
        return f"{self.__class__.__name__}({repr(url)})"
