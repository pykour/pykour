"""Security headers middleware for Pykour."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pykour.middleware.base import BaseMiddleware
from pykour.middleware.utils import is_path_excluded
from pykour.types import Receive, Scope, Send


@dataclass
class ContentSecurityPolicy:
    """Content Security Policy configuration.

    Example:
        csp = ContentSecurityPolicy(
            default_src=["'self'"],
            script_src=["'self'", "https://cdn.example.com"],
            style_src=["'self'", "'unsafe-inline'"],
            img_src=["'self'", "data:", "https:"],
        )
    """

    default_src: list[str] = field(default_factory=lambda: ["'self'"])
    script_src: list[str] | None = None
    style_src: list[str] | None = None
    img_src: list[str] | None = None
    font_src: list[str] | None = None
    connect_src: list[str] | None = None
    media_src: list[str] | None = None
    object_src: list[str] | None = None
    frame_src: list[str] | None = None
    frame_ancestors: list[str] | None = None
    form_action: list[str] | None = None
    base_uri: list[str] | None = None
    report_uri: str | None = None
    report_to: str | None = None
    upgrade_insecure_requests: bool = False
    block_all_mixed_content: bool = False

    def to_header(self) -> str:
        """Convert to CSP header value.

        Returns:
            CSP header string.
        """
        directives = []

        # Add default-src first
        directives.append(f"default-src {' '.join(self.default_src)}")

        # Add other directives if set
        directive_map = {
            "script-src": self.script_src,
            "style-src": self.style_src,
            "img-src": self.img_src,
            "font-src": self.font_src,
            "connect-src": self.connect_src,
            "media-src": self.media_src,
            "object-src": self.object_src,
            "frame-src": self.frame_src,
            "frame-ancestors": self.frame_ancestors,
            "form-action": self.form_action,
            "base-uri": self.base_uri,
        }

        for directive_name, sources in directive_map.items():
            if sources:
                directives.append(f"{directive_name} {' '.join(sources)}")

        # Add boolean directives
        if self.upgrade_insecure_requests:
            directives.append("upgrade-insecure-requests")
        if self.block_all_mixed_content:
            directives.append("block-all-mixed-content")

        # Add reporting directives
        if self.report_uri:
            directives.append(f"report-uri {self.report_uri}")
        if self.report_to:
            directives.append(f"report-to {self.report_to}")

        return "; ".join(directives)


class SecurityHeadersMiddleware(BaseMiddleware):
    """Middleware that adds security headers to responses.

    Adds common security headers to protect against various attacks:
    - XSS (Cross-Site Scripting)
    - Clickjacking
    - MIME type sniffing
    - Protocol downgrade attacks

    Example:
        # Basic usage with defaults
        app.add_middleware(SecurityHeadersMiddleware)

        # Custom configuration
        app.add_middleware(
            SecurityHeadersMiddleware,
            hsts_max_age=31536000,  # 1 year
            hsts_include_subdomains=True,
            hsts_preload=True,
            content_security_policy=ContentSecurityPolicy(
                default_src=["'self'"],
                script_src=["'self'", "https://cdn.example.com"],
            ),
        )

        # Disable specific headers
        app.add_middleware(
            SecurityHeadersMiddleware,
            x_frame_options=None,  # Disable X-Frame-Options
        )
    """

    def __init__(
        self,
        app: Any,
        *,
        # HSTS (HTTP Strict Transport Security)
        hsts_max_age: int | None = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        # X-Content-Type-Options
        x_content_type_options: str | None = "nosniff",
        # X-Frame-Options
        x_frame_options: str | None = "DENY",
        # X-XSS-Protection (legacy, explicitly disabled as "1; mode=block" can
        # introduce vulnerabilities; use CSP instead for XSS protection)
        x_xss_protection: str | None = "0",
        # Referrer-Policy
        referrer_policy: str | None = "strict-origin-when-cross-origin",
        # Content-Security-Policy
        content_security_policy: ContentSecurityPolicy | str | None = None,
        csp_report_only: bool = False,
        # Permissions-Policy (formerly Feature-Policy)
        permissions_policy: dict[str, list[str]] | None = None,
        # Cross-Origin policies
        cross_origin_embedder_policy: str | None = None,
        cross_origin_opener_policy: str | None = None,
        cross_origin_resource_policy: str | None = None,
        # Cache-Control for security-sensitive pages
        cache_control: str | None = None,
        # Exclude paths from security headers
        exclude_paths: list[str] | None = None,
    ) -> None:
        """Initialize security headers middleware.

        Args:
            app: The ASGI application to wrap.
            hsts_max_age: Max age for HSTS in seconds. None to disable.
            hsts_include_subdomains: Include subdomains in HSTS.
            hsts_preload: Enable HSTS preload.
            x_content_type_options: X-Content-Type-Options header value.
            x_frame_options: X-Frame-Options header value (DENY or SAMEORIGIN).
            x_xss_protection: X-XSS-Protection header value.
            referrer_policy: Referrer-Policy header value.
            content_security_policy: CSP configuration.
            csp_report_only: Use Content-Security-Policy-Report-Only header.
            permissions_policy: Permissions-Policy directives.
            cross_origin_embedder_policy: COEP header value.
            cross_origin_opener_policy: COOP header value.
            cross_origin_resource_policy: CORP header value.
            cache_control: Cache-Control header for security pages.
            exclude_paths: Paths to exclude from security headers.
        """
        super().__init__(app)

        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.x_content_type_options = x_content_type_options
        self.x_frame_options = x_frame_options
        self.x_xss_protection = x_xss_protection
        self.referrer_policy = referrer_policy
        self.content_security_policy = content_security_policy
        self.csp_report_only = csp_report_only
        self.permissions_policy = permissions_policy
        self.cross_origin_embedder_policy = cross_origin_embedder_policy
        self.cross_origin_opener_policy = cross_origin_opener_policy
        self.cross_origin_resource_policy = cross_origin_resource_policy
        self.cache_control = cache_control
        self.exclude_paths = list(exclude_paths or [])

        # Pre-compute static headers
        self._headers = self._build_headers()

    def _build_headers(self) -> list[tuple[bytes, bytes]]:
        """Build the list of security headers to add.

        Returns:
            List of header tuples (name, value).
        """
        headers: list[tuple[bytes, bytes]] = []

        # HSTS
        if self.hsts_max_age is not None:
            hsts_value = f"max-age={self.hsts_max_age}"
            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.hsts_preload:
                hsts_value += "; preload"
            headers.append((b"strict-transport-security", hsts_value.encode()))

        # X-Content-Type-Options
        if self.x_content_type_options:
            headers.append(
                (b"x-content-type-options", self.x_content_type_options.encode())
            )

        # X-Frame-Options
        if self.x_frame_options:
            headers.append((b"x-frame-options", self.x_frame_options.encode()))

        # X-XSS-Protection
        if self.x_xss_protection:
            headers.append((b"x-xss-protection", self.x_xss_protection.encode()))

        # Referrer-Policy
        if self.referrer_policy:
            headers.append((b"referrer-policy", self.referrer_policy.encode()))

        # Content-Security-Policy
        if self.content_security_policy:
            if isinstance(self.content_security_policy, ContentSecurityPolicy):
                csp_value = self.content_security_policy.to_header()
            else:
                csp_value = self.content_security_policy

            header_name = (
                b"content-security-policy-report-only"
                if self.csp_report_only
                else b"content-security-policy"
            )
            headers.append((header_name, csp_value.encode()))

        # Permissions-Policy
        if self.permissions_policy:
            policy_parts = []
            for feature, origins in self.permissions_policy.items():
                if origins:
                    # Convert to Permissions-Policy format
                    # "self" and "*" are keywords and must not be quoted
                    origin_str = " ".join(
                        o if o in ("self", "*") else f'"{o}"' for o in origins
                    )
                    policy_parts.append(f"{feature}=({origin_str})")
                else:
                    policy_parts.append(f"{feature}=()")
            headers.append((b"permissions-policy", ", ".join(policy_parts).encode()))

        # Cross-Origin policies
        if self.cross_origin_embedder_policy:
            headers.append(
                (
                    b"cross-origin-embedder-policy",
                    self.cross_origin_embedder_policy.encode(),
                )
            )
        if self.cross_origin_opener_policy:
            headers.append(
                (
                    b"cross-origin-opener-policy",
                    self.cross_origin_opener_policy.encode(),
                )
            )
        if self.cross_origin_resource_policy:
            headers.append(
                (
                    b"cross-origin-resource-policy",
                    self.cross_origin_resource_policy.encode(),
                )
            )

        # Cache-Control
        if self.cache_control:
            headers.append((b"cache-control", self.cache_control.encode()))

        return headers

    def _should_add_headers(self, path: str) -> bool:
        """Check if headers should be added for this path.

        Args:
            path: Request path.

        Returns:
            True if headers should be added.
        """
        return not is_path_excluded(path, self.exclude_paths)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        """Handle ASGI request and add security headers."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "/")

        if not self._should_add_headers(path):
            await self.app(scope, receive, send)
            return

        async def send_with_security_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                # Add security headers
                headers.extend(self._headers)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
