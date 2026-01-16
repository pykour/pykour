"""OpenAPI configuration."""

from dataclasses import dataclass


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
    # Internal options
    include_head_operations: bool = False
    include_options_operations: bool = False
