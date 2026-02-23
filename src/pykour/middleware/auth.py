"""JWT authentication middleware for Pykour."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Sequence

from pykour.middleware.base import BaseMiddleware, Receive, Scope, Send
from pykour.middleware.utils import extract_bearer_token
from pykour.response import JSONResponse

# Base64 encodes 3 bytes into 4 characters, requiring padding to multiple of 4
_BASE64_GROUP_SIZE = 4


def _urlsafe_b64encode_nopad(data: bytes) -> str:
    """Encode bytes to base64url string without padding (JWT format)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


class JWTAuthMiddleware(BaseMiddleware):
    """JWT (JSON Web Token) authentication middleware.

    This middleware extracts and validates JWT tokens from the Authorization
    header. On successful validation, the decoded payload is stored in the
    ASGI scope under 'user' key, accessible via request.state.user.

    Supports key rotation by accepting multiple secret keys. During rotation,
    tokens signed with any of the provided keys will be accepted, allowing
    graceful migration to new keys.

    Example:
        # Basic usage
        app.add_middleware(
            JWTAuthMiddleware,
            secret_key="your-secret-key",
        )

        # With custom configuration
        app.add_middleware(
            JWTAuthMiddleware,
            secret_key="your-secret-key",
            algorithm="HS256",
            exclude_paths=["/health", "/login", "/register"],
            auto_error=True,
        )

        # Key rotation (accepts tokens signed with any key)
        app.add_middleware(
            JWTAuthMiddleware,
            secret_keys=["new-secret-key", "old-secret-key"],
        )

        # In route handler
        async def get(request: Request) -> JSONResponse:
            user = request.state.user
            return JSONResponse({"user_id": user["sub"]})
    """

    def __init__(
        self,
        app: Any,
        *,
        secret_key: str | None = None,
        secret_keys: Sequence[str] | None = None,
        algorithm: str = "HS256",
        exclude_paths: Sequence[str] = (),
        auto_error: bool = True,
    ) -> None:
        """Initialize JWT authentication middleware.

        Args:
            app: The ASGI application to wrap.
            secret_key: Secret key used for token signature verification.
                       Deprecated in favor of secret_keys for key rotation.
            secret_keys: List of secret keys for token verification. The first
                        key is used for signing new tokens. All keys are tried
                        during verification, enabling graceful key rotation.
            algorithm: JWT signing algorithm. Currently only HS256 is supported.
            exclude_paths: List of paths to exclude from authentication.
            auto_error: If True, return 401 response for invalid tokens.
                       If False, continue without setting user data.

        Raises:
            ValueError: If neither secret_key nor secret_keys is provided,
                       or if both are provided, or if secret_keys is empty.
        """
        super().__init__(app)

        # Validate key configuration
        if secret_key is not None and secret_keys is not None:
            raise ValueError(
                "Cannot specify both 'secret_key' and 'secret_keys'. "
                "Use 'secret_keys' for key rotation support."
            )

        if secret_key is None and secret_keys is None:
            raise ValueError("Either 'secret_key' or 'secret_keys' must be provided.")

        if secret_keys is not None and len(secret_keys) == 0:
            raise ValueError("'secret_keys' cannot be empty.")

        # Store keys as list (for rotation support)
        if secret_keys is not None:
            self._secret_keys = list(secret_keys)
        else:
            # secret_key must be non-None here due to earlier validation
            assert secret_key is not None
            self._secret_keys = [secret_key]

        self.algorithm = algorithm
        self.exclude_paths = list(exclude_paths)
        self.auto_error = auto_error

        if algorithm != "HS256":
            raise ValueError(
                f"Unsupported algorithm: {algorithm}. Only HS256 is supported."
            )

    @property
    def secret_key(self) -> str:
        """Get the primary secret key (first in the list)."""
        return self._secret_keys[0]

    @property
    def secret_keys(self) -> list[str]:
        """Get all secret keys for verification."""
        return self._secret_keys.copy()

    def _b64decode(self, data: str) -> bytes:
        """Decode base64url encoded string.

        JWT uses base64url encoding without padding.
        """
        # Add padding if needed
        padding = _BASE64_GROUP_SIZE - len(data) % _BASE64_GROUP_SIZE
        if padding != _BASE64_GROUP_SIZE:
            data += "=" * padding
        return base64.urlsafe_b64decode(data)

    def _sign(self, message: bytes, key: str | None = None) -> bytes:
        """Sign message with HMAC-SHA256.

        Args:
            message: Message bytes to sign.
            key: Secret key to use. Defaults to primary key.
        """
        secret = key if key is not None else self.secret_key
        return hmac.new(
            secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).digest()

    def _verify_signature(self, message: bytes, signature: bytes, key: str) -> bool:
        """Verify signature with a specific key.

        Args:
            message: Original message bytes.
            signature: Signature bytes to verify.
            key: Secret key to use for verification.

        Returns:
            True if signature is valid, False otherwise.
        """
        expected_sig = self._sign(message, key)
        return hmac.compare_digest(expected_sig, signature)

    def _verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify and decode JWT token.

        Tries all configured secret keys during verification to support
        key rotation. Signature is considered valid if it matches any key.

        Returns:
            Decoded payload dict if valid, None otherwise.
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, signature_b64 = parts

            # Decode signature
            message = f"{header_b64}.{payload_b64}".encode("ascii")
            actual_sig = self._b64decode(signature_b64)

            # Try verification with each key (for key rotation support)
            signature_valid = False
            for key in self._secret_keys:
                if self._verify_signature(message, actual_sig, key):
                    signature_valid = True
                    break

            if not signature_valid:
                return None

            # Decode and verify header
            header = json.loads(self._b64decode(header_b64).decode("utf-8"))
            if header.get("alg") != self.algorithm:
                return None

            # Decode payload
            payload = json.loads(self._b64decode(payload_b64).decode("utf-8"))

            # Check expiration
            if "exp" in payload:
                if time.time() > payload["exp"]:
                    return None

            # Check not-before time
            if "nbf" in payload:
                if time.time() < payload["nbf"]:
                    return None

            return payload

        except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    def _unauthorized_response(self, detail: str) -> JSONResponse:
        """Create 401 Unauthorized response."""
        return JSONResponse(
            {"detail": detail},
            status_code=401,
            headers={"WWW-Authenticate": "Bearer"},
        )

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request with JWT authentication."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")

        # Skip authentication for excluded paths
        if not self.should_process_path(path, self.exclude_paths):
            await self.app(scope, receive, send)
            return

        # Extract token from Authorization header
        token = extract_bearer_token(scope)
        if token is None:
            if self.auto_error:
                response = self._unauthorized_response("Missing authentication token")
                await response(scope, receive, send)
                return
            await self.app(scope, receive, send)
            return

        # Verify token
        payload = self._verify_token(token)
        if payload is None:
            if self.auto_error:
                response = self._unauthorized_response("Invalid or expired token")
                await response(scope, receive, send)
                return
            await self.app(scope, receive, send)
            return

        # Store user info in scope for access via request.state.user
        scope["user"] = payload

        await self.app(scope, receive, send)


def create_jwt_token(
    payload: dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_in: int | None = None,
) -> str:
    """Create a JWT token.

    This is a helper function for creating tokens for testing
    or simple use cases. For production, consider using a dedicated
    JWT library.

    Args:
        payload: Token payload data. May include "exp" claim directly.
        secret_key: Secret key for signing.
        algorithm: Signing algorithm (only HS256 supported).
        expires_in: Expiration time in seconds from now. Cannot be used
            if payload already contains "exp" claim.

    Returns:
        Encoded JWT token string.

    Raises:
        ValueError: If both payload contains "exp" and expires_in is provided,
            or if an unsupported algorithm is specified.
    """
    if algorithm != "HS256":
        raise ValueError(
            f"Unsupported algorithm: {algorithm}. Only HS256 is supported."
        )

    # Check for conflicting expiration settings
    if "exp" in payload and expires_in is not None:
        raise ValueError(
            "Cannot specify both 'exp' in payload and 'expires_in' parameter; "
            "use one or the other to set token expiration"
        )

    # Create header
    header = {"alg": algorithm, "typ": "JWT"}

    # Add expiration if specified via expires_in parameter
    token_payload = dict(payload)
    if expires_in is not None:
        token_payload["exp"] = int(time.time()) + expires_in

    # Encode header and payload
    header_b64 = _urlsafe_b64encode_nopad(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    payload_b64 = _urlsafe_b64encode_nopad(
        json.dumps(token_payload, separators=(",", ":")).encode("utf-8")
    )

    # Create signature
    message = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message,
        hashlib.sha256,
    ).digest()
    signature_b64 = _urlsafe_b64encode_nopad(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"
