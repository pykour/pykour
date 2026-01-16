"""OpenAPI 3.1 specification data models."""

from typing import Any, TypedDict


class ContactObject(TypedDict, total=False):
    """Contact information for the exposed API."""

    name: str
    url: str
    email: str


class LicenseObject(TypedDict, total=False):
    """License information for the exposed API."""

    name: str  # Required
    identifier: str
    url: str


class InfoObject(TypedDict, total=False):
    """Metadata about the API."""

    title: str  # Required
    summary: str
    description: str
    termsOfService: str
    contact: ContactObject
    license: LicenseObject
    version: str  # Required


class ServerVariableObject(TypedDict, total=False):
    """Server variable for URL template substitution."""

    enum: list[str]
    default: str  # Required
    description: str


class ServerObject(TypedDict, total=False):
    """Server object representing a server."""

    url: str  # Required
    description: str
    variables: dict[str, ServerVariableObject]


class ExternalDocumentationObject(TypedDict, total=False):
    """External documentation reference."""

    description: str
    url: str  # Required


class TagObject(TypedDict, total=False):
    """Tag for API documentation control."""

    name: str  # Required
    description: str
    externalDocs: ExternalDocumentationObject


class ReferenceObject(TypedDict):
    """Reference to other components."""

    # Using $ prefix for JSON Schema reference
    pass


class SchemaObject(TypedDict, total=False):
    """JSON Schema object for OpenAPI."""

    type: str
    format: str
    title: str
    description: str
    default: Any
    enum: list[Any]
    const: Any
    # Numeric constraints
    minimum: float | int
    maximum: float | int
    exclusiveMinimum: float | int
    exclusiveMaximum: float | int
    multipleOf: float | int
    # String constraints
    minLength: int
    maxLength: int
    pattern: str
    # Array constraints
    items: "SchemaObject | dict[str, Any]"
    minItems: int
    maxItems: int
    uniqueItems: bool
    # Object constraints
    properties: dict[str, "SchemaObject | dict[str, Any]"]
    required: list[str]
    additionalProperties: bool | "SchemaObject | dict[str, Any]"
    # Composition
    allOf: list["SchemaObject | dict[str, Any]"]
    oneOf: list["SchemaObject | dict[str, Any]"]
    anyOf: list["SchemaObject | dict[str, Any]"]
    # Reference
    # $ref is handled separately


class ExampleObject(TypedDict, total=False):
    """Example object."""

    summary: str
    description: str
    value: Any
    externalValue: str


class EncodingObject(TypedDict, total=False):
    """Encoding object for multipart request bodies."""

    contentType: str
    headers: dict[str, Any]
    style: str
    explode: bool
    allowReserved: bool


class MediaTypeObject(TypedDict, total=False):
    """Media type object."""

    schema: SchemaObject | dict[str, Any]
    example: Any
    examples: dict[str, ExampleObject | dict[str, Any]]
    encoding: dict[str, EncodingObject]


class ParameterObject(TypedDict, total=False):
    """Parameter object for path, query, header, or cookie parameters."""

    name: str  # Required
    # in: Required - "query", "header", "path", "cookie"
    description: str
    required: bool
    deprecated: bool
    allowEmptyValue: bool
    style: str
    explode: bool
    allowReserved: bool
    schema: SchemaObject | dict[str, Any]
    example: Any
    examples: dict[str, ExampleObject | dict[str, Any]]
    content: dict[str, MediaTypeObject]


class RequestBodyObject(TypedDict, total=False):
    """Request body object."""

    description: str
    content: dict[str, MediaTypeObject]  # Required
    required: bool


class HeaderObject(TypedDict, total=False):
    """Header object."""

    description: str
    required: bool
    deprecated: bool
    schema: SchemaObject | dict[str, Any]


class LinkObject(TypedDict, total=False):
    """Link object for response links."""

    operationRef: str
    operationId: str
    parameters: dict[str, Any]
    requestBody: Any
    description: str
    server: ServerObject


class ResponseObject(TypedDict, total=False):
    """Response object."""

    description: str  # Required
    headers: dict[str, HeaderObject | dict[str, Any]]
    content: dict[str, MediaTypeObject]
    links: dict[str, LinkObject | dict[str, Any]]


class OperationObject(TypedDict, total=False):
    """Operation object for a single API operation."""

    tags: list[str]
    summary: str
    description: str
    externalDocs: ExternalDocumentationObject
    operationId: str
    parameters: list[ParameterObject | dict[str, Any]]
    requestBody: RequestBodyObject | dict[str, Any]
    responses: dict[str, ResponseObject | dict[str, Any]]
    callbacks: dict[str, dict[str, Any]]
    deprecated: bool
    security: list[dict[str, list[str]]]
    servers: list[ServerObject]


class PathItemObject(TypedDict, total=False):
    """Path item object."""

    summary: str
    description: str
    get: OperationObject
    put: OperationObject
    post: OperationObject
    delete: OperationObject
    options: OperationObject
    head: OperationObject
    patch: OperationObject
    trace: OperationObject
    servers: list[ServerObject]
    parameters: list[ParameterObject | dict[str, Any]]


class ComponentsObject(TypedDict, total=False):
    """Components object for reusable schemas."""

    schemas: dict[str, SchemaObject | dict[str, Any]]
    responses: dict[str, ResponseObject | dict[str, Any]]
    parameters: dict[str, ParameterObject | dict[str, Any]]
    examples: dict[str, ExampleObject | dict[str, Any]]
    requestBodies: dict[str, RequestBodyObject | dict[str, Any]]
    headers: dict[str, HeaderObject | dict[str, Any]]
    securitySchemes: dict[str, dict[str, Any]]
    links: dict[str, LinkObject | dict[str, Any]]
    callbacks: dict[str, dict[str, Any]]
    pathItems: dict[str, PathItemObject | dict[str, Any]]


class OpenAPIDocument(TypedDict, total=False):
    """Root OpenAPI document object."""

    openapi: str  # Required - "3.1.0"
    info: InfoObject  # Required
    jsonSchemaDialect: str
    servers: list[ServerObject]
    paths: dict[str, PathItemObject]
    webhooks: dict[str, PathItemObject | dict[str, Any]]
    components: ComponentsObject
    security: list[dict[str, list[str]]]
    tags: list[TagObject]
    externalDocs: ExternalDocumentationObject
