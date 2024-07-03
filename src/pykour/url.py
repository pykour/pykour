from __future__ import annotations

from typing import Any, MutableMapping
from urllib.parse import (
    SplitResult,
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
    quote,
    unquote,
)


class URL:
    """URL is a class that represents a URL."""

    def __init__(self, url: str = "", scope: MutableMapping[str, Any] = None) -> None:
        """URL is a class that represents a URL.

        Args:
            url: The URL.
            scope: The ASGI scope.
        """
        if scope is not None:
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
            elif server is None:
                url = path
            else:
                host, port = server
                default_port = {"http": 80, "https": 443, "ws": 80, "wss": 443}[scheme]
                if port == default_port:
                    url = f"{scheme}://{host}{path}"
                else:
                    url = f"{scheme}://{host}:{port}{path}"

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
    def netloc(self) -> str:
        """Returns the network location.

        Returns:
            The network location.
        """
        return self.components.netloc

    @property
    def path(self) -> str:
        """Returns the path.

        Returns:
            The path.
        """
        return self.components.path

    @property
    def query(self) -> str:
        """Returns the query string.

        Returns:
            The query string.
        """
        return self.components.query

    @property
    def fragment(self) -> str:
        """Returns the fragment.

        Returns:
            The fragment.
        """
        return self.components.fragment

    @property
    def username(self) -> str:
        """Returns the username.

        Returns:
            The username.
        """
        return self.components.username

    @property
    def password(self) -> str:
        """Returns the password.

        Returns:
            The password.
        """
        return self.components.password

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
        return self.components.port

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

    def normalize(self) -> URL:
        scheme = self.scheme.lower()
        netloc = self.netloc.lower()
        path = quote(unquote(self.path))
        query = urlencode(sorted(parse_qsl(self.query)))
        fragment = self.fragment
        return self.__class__(urlunsplit((scheme, netloc, path, query, fragment)))

    def replace(self, **kwargs) -> URL:
        if "username" in kwargs or "password" in kwargs or "hostname" in kwargs or "port" in kwargs:
            hostname = kwargs.pop("hostname", None)
            port = kwargs.pop("port", self.port)
            username = kwargs.pop("username", self.username)
            password = kwargs.pop("password", self.password)

            if hostname is None:
                netloc = self.netloc
                _, _, hostname = netloc.rpartition("@")

                if hostname[-1] != "]":
                    hostname = hostname.rsplit(":", 1)[0]

            netloc = hostname
            if port is not None:
                netloc += f":{port}"
            if username is not None:
                userpass = username
                if password is not None:
                    userpass += f":{password}"
                netloc = f"{userpass}@{netloc}"

            kwargs["netloc"] = netloc

        components = self.components._replace(**kwargs)
        return self.__class__(components.geturl())

    def __eq__(self, other: Any) -> bool:
        return str(self) == str(other)

    def __str__(self) -> str:
        return self.url

    def __repr__(self) -> str:
        url = str(self)
        if self.password:
            url = str(self.replace(password="********"))
        return f"{self.__class__.__name__}({repr(url)})"
