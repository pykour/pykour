"""Cookie management for test client."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Iterator

logger = logging.getLogger("pykour.testing")


@dataclass
class Cookie:
    """Represents a single HTTP cookie.

    Attributes:
        name: Cookie name.
        value: Cookie value.
        path: Path for which the cookie is valid.
        domain: Domain for which the cookie is valid.
        expires: Expiration timestamp (Unix time).
        max_age: Max age in seconds.
        secure: Whether the cookie requires HTTPS.
        httponly: Whether the cookie is HTTP-only.
        samesite: SameSite attribute (Strict, Lax, or None).
    """

    name: str
    value: str
    path: str = "/"
    domain: str | None = None
    expires: float | None = None
    max_age: int | None = None
    secure: bool = False
    httponly: bool = False
    samesite: str | None = "Lax"

    def is_expired(self) -> bool:
        """Check if the cookie has expired.

        Returns:
            True if the cookie has expired, False otherwise.
        """
        if self.max_age is not None:
            if self.max_age <= 0:
                return True
        if self.expires is not None:
            return time.time() > self.expires
        return False


class CookieJar:
    """Cookie container with automatic management.

    Handles Set-Cookie header parsing and Cookie header generation.
    Automatically manages cookie expiration and path matching.

    Example:
        jar = CookieJar()
        jar.set("session", "abc123", path="/app")
        header = jar.get_cookie_header("/app/dashboard")
        # header == "session=abc123"
    """

    def __init__(self) -> None:
        """Initialize an empty cookie jar."""
        self._cookies: dict[str, Cookie] = {}

    def set(
        self,
        name: str,
        value: str,
        *,
        path: str = "/",
        domain: str | None = None,
        expires: float | None = None,
        max_age: int | None = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: str | None = "Lax",
    ) -> None:
        """Set a cookie manually.

        Args:
            name: Cookie name.
            value: Cookie value.
            path: Path for which the cookie is valid.
            domain: Domain for which the cookie is valid.
            expires: Expiration timestamp (Unix time).
            max_age: Max age in seconds.
            secure: Whether the cookie requires HTTPS.
            httponly: Whether the cookie is HTTP-only.
            samesite: SameSite attribute.
        """
        self._cookies[name] = Cookie(
            name=name,
            value=value,
            path=path,
            domain=domain,
            expires=expires,
            max_age=max_age,
            secure=secure,
            httponly=httponly,
            samesite=samesite,
        )

    def get(self, name: str, default: str | None = None) -> str | None:
        """Get a cookie value by name.

        Args:
            name: Cookie name.
            default: Default value if cookie not found or expired.

        Returns:
            Cookie value or default.
        """
        cookie = self._cookies.get(name)
        if cookie and not cookie.is_expired():
            return cookie.value
        return default

    def delete(self, name: str) -> None:
        """Delete a cookie by name.

        Args:
            name: Cookie name to delete.
        """
        self._cookies.pop(name, None)

    def clear(self) -> None:
        """Clear all cookies from the jar."""
        self._cookies.clear()

    def update_from_response(self, raw_headers: list[tuple[str, str]]) -> None:
        """Parse Set-Cookie headers and update the jar.

        Args:
            raw_headers: List of (name, value) header tuples.
        """
        for key, value in raw_headers:
            if key.lower() == "set-cookie":
                cookie = self.parse_set_cookie(value)
                if cookie.max_age == 0 or (
                    cookie.expires is not None and cookie.expires <= time.time()
                ):
                    # Delete cookie if max-age is 0 or already expired
                    self._cookies.pop(cookie.name, None)
                else:
                    self._cookies[cookie.name] = cookie

    def get_cookie_header(self, path: str = "/") -> str:
        """Generate Cookie header value for a request.

        Args:
            path: Request path for path matching.

        Returns:
            Cookie header value (e.g., "name1=value1; name2=value2").
        """
        valid_cookies: list[str] = []
        for cookie in self._cookies.values():
            if not cookie.is_expired() and path.startswith(cookie.path):
                valid_cookies.append(f"{cookie.name}={cookie.value}")
        return "; ".join(valid_cookies)

    def __iter__(self) -> Iterator[Cookie]:
        """Iterate over all cookies in the jar."""
        return iter(self._cookies.values())

    def __len__(self) -> int:
        """Return the number of cookies in the jar."""
        return len(self._cookies)

    def __contains__(self, name: str) -> bool:
        """Check if a cookie exists in the jar.

        Args:
            name: Cookie name.

        Returns:
            True if the cookie exists and is not expired.
        """
        cookie = self._cookies.get(name)
        return cookie is not None and not cookie.is_expired()

    @staticmethod
    def parse_set_cookie(header_value: str) -> Cookie:
        """Parse a Set-Cookie header value into a Cookie object.

        Args:
            header_value: Set-Cookie header value.

        Returns:
            Parsed Cookie object.

        Example:
            cookie = CookieJar.parse_set_cookie(
                "session=abc123; Path=/; HttpOnly; Secure; Max-Age=3600"
            )
            assert cookie.name == "session"
            assert cookie.httponly is True
        """
        parts = header_value.split(";")
        name_value = parts[0].strip()
        name, _, value = name_value.partition("=")

        cookie = Cookie(name=name.strip(), value=value.strip())

        for part in parts[1:]:
            part = part.strip()
            if "=" in part:
                attr_key, _, attr_val = part.partition("=")
                attr_key = attr_key.strip().lower()
                attr_val = attr_val.strip()
                if attr_key == "path":
                    cookie.path = attr_val
                elif attr_key == "domain":
                    cookie.domain = attr_val
                elif attr_key == "max-age":
                    try:
                        cookie.max_age = int(attr_val)
                    except ValueError:
                        logger.debug(
                            "Invalid max-age value in Set-Cookie header: %s", attr_val
                        )
                elif attr_key == "expires":
                    try:
                        dt = parsedate_to_datetime(attr_val)
                        cookie.expires = dt.timestamp()
                    except (ValueError, TypeError):
                        logger.debug(
                            "Invalid expires value in Set-Cookie header: %s", attr_val
                        )
                elif attr_key == "samesite":
                    cookie.samesite = attr_val
            else:
                flag = part.lower()
                if flag == "secure":
                    cookie.secure = True
                elif flag == "httponly":
                    cookie.httponly = True

        return cookie
