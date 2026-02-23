"""Testing utilities for Pykour applications."""

from __future__ import annotations

from typing import Any

from pykour.testing.client import (
    AuthTestClient,
    SyncTestClient,
    TestClient,
    TestResponse,
)
from pykour.testing.cookies import Cookie, CookieJar
from pykour.testing.websocket import WebSocketTestSession, WebSocketTestSessionClosed


def make_jwt_token(
    payload: dict[str, Any] | None = None,
    secret_key: str = "test-secret-key",
    *,
    expires_in: int | None = 3600,
    scopes: str | list[str] | None = None,
    roles: list[str] | None = None,
    subject: str | None = None,
) -> str:
    """Create a JWT token for testing purposes.

    A convenience helper that wraps ``create_jwt_token`` from the auth
    middleware with sensible defaults for test scenarios.

    Args:
        payload: Custom JWT payload claims. Merged with other arguments.
        secret_key: Secret key for signing the token.
        expires_in: Expiration time in seconds from now. None for no expiration.
        scopes: Scopes to include. A string is used as-is; a list is joined
            with spaces.
        roles: Roles list to include in the token.
        subject: Subject (``sub``) claim.

    Returns:
        Encoded JWT token string.
    """
    from pykour.middleware.auth import create_jwt_token

    token_payload: dict[str, Any] = {}
    if subject is not None:
        token_payload["sub"] = subject
    if scopes is not None:
        if isinstance(scopes, list):
            token_payload["scope"] = " ".join(scopes)
        else:
            token_payload["scope"] = scopes
    if roles is not None:
        token_payload["roles"] = roles
    if payload is not None:
        token_payload.update(payload)

    return create_jwt_token(
        token_payload,
        secret_key,
        expires_in=expires_in,
    )


__all__ = [
    "AuthTestClient",
    "TestClient",
    "TestResponse",
    "SyncTestClient",
    "Cookie",
    "CookieJar",
    "WebSocketTestSession",
    "WebSocketTestSessionClosed",
    "make_jwt_token",
]
