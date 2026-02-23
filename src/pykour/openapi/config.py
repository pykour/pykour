"""OpenAPI configuration."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ContactInfo:
    """Contact information for the API."""

    name: str | None = None
    url: str | None = None
    email: str | None = None


@dataclass
class LicenseInfo:
    """License information for the API."""

    name: str
    identifier: str | None = None
    url: str | None = None


@dataclass
class ServerInfo:
    """Server information."""

    url: str
    description: str | None = None
    variables: dict[str, dict[str, str]] | None = None


@dataclass
class OAuthFlow:
    """OAuth 2.0 flow configuration."""

    authorization_url: str | None = None
    token_url: str | None = None
    refresh_url: str | None = None
    scopes: dict[str, str] = field(default_factory=dict)


@dataclass
class SecuritySchemeConfig:
    """Security scheme configuration for OpenAPI documentation."""

    type: Literal["http", "apiKey", "oauth2", "openIdConnect"]
    scheme: str | None = None
    bearer_format: str | None = None
    name: str | None = None
    api_key_in: Literal["header", "query", "cookie"] | None = None
    flows: dict[str, OAuthFlow] | None = None
    open_id_connect_url: str | None = None
    description: str | None = None


@dataclass
class OpenAPIConfig:
    """Configuration for OpenAPI documentation generation."""

    title: str = "Pykour API"
    version: str = "1.0.0"
    description: str | None = None
    summary: str | None = None
    terms_of_service: str | None = None
    contact: ContactInfo | None = None
    license: LicenseInfo | None = None
    servers: list[ServerInfo] | None = None
    openapi_version: str = "3.1.0"
    docs_url: str | None = "/docs"
    openapi_url: str | None = "/openapi.json"
    redoc_url: str | None = "/redoc"
    tags: list[dict[str, str]] | None = None
    security_schemes: dict[str, SecuritySchemeConfig] | None = None
    global_security: list[dict[str, list[str]]] | None = None
    # Internal options
    include_head_operations: bool = False
    include_options_operations: bool = False


def jwt_bearer_scheme(
    name: str = "bearerAuth",
    description: str | None = None,
    bearer_format: str = "JWT",
) -> dict[str, SecuritySchemeConfig]:
    """Create a JWT Bearer security scheme configuration.

    Args:
        name: The scheme name used in the OpenAPI document.
        description: Optional description of the scheme.
        bearer_format: Format of the bearer token (default "JWT").

    Returns:
        Dictionary mapping scheme name to SecuritySchemeConfig.
    """
    return {
        name: SecuritySchemeConfig(
            type="http",
            scheme="bearer",
            bearer_format=bearer_format,
            description=description,
        )
    }


def api_key_scheme(
    name: str = "apiKeyAuth",
    header_name: str = "X-API-Key",
    description: str | None = None,
) -> dict[str, SecuritySchemeConfig]:
    """Create an API Key security scheme configuration.

    Args:
        name: The scheme name used in the OpenAPI document.
        header_name: The name of the header that contains the API key.
        description: Optional description of the scheme.

    Returns:
        Dictionary mapping scheme name to SecuritySchemeConfig.
    """
    return {
        name: SecuritySchemeConfig(
            type="apiKey",
            name=header_name,
            api_key_in="header",
            description=description,
        )
    }
