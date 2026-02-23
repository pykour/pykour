"""Pykour - A lightweight ASGI web framework."""

from pykour.application import Pykour
from pykour.config import PykourConfig, load_config
from pykour.exception_handlers import ExceptionHandler, ExceptionHandlerRegistry
from pykour.exceptions import (
    BadGatewayException,
    BadRequestException,
    ConflictException,
    ExpectationFailedException,
    FailedDependencyException,
    ForbiddenException,
    GatewayTimeoutException,
    GoneException,
    HTTPException,
    HTTPVersionNotSupportedException,
    ImATeapotException,
    InsufficientStorageException,
    InternalServerErrorException,
    LengthRequiredException,
    LockedException,
    LoopDetectedException,
    MethodNotAllowedException,
    MisdirectedRequestException,
    NetworkAuthenticationRequiredException,
    NotAcceptableException,
    NotExtendedException,
    NotFoundException,
    NotImplementedException,
    PayloadTooLargeException,
    PaymentRequiredException,
    PreconditionFailedException,
    PreconditionRequiredException,
    ProxyAuthenticationRequiredException,
    RangeNotSatisfiableException,
    RequestHeaderFieldsTooLargeException,
    RequestTimeoutException,
    ServiceUnavailableException,
    TooEarlyException,
    TooManyRequestsException,
    UnauthorizedException,
    UnavailableForLegalReasonsException,
    UnprocessableEntityException,
    UnsupportedMediaTypeException,
    UpgradeRequiredException,
    URITooLongException,
    VariantAlsoNegotiatesException,
)
from pykour.logging.context import get_trace_id
from pykour.middleware import BaseMiddleware
from pykour.request import Request
from pykour.response import (
    EventSourceResponse,
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
    ServerSentEvent,
    StreamingResponse,
)
from pykour.websocket import WebSocket, WebSocketDisconnect, WebSocketState
from pykour.datastructures import UploadFile
from pykour.schema import (
    Body,
    Field,
    File,
    Form,
    Path,
    Query,
    Schema,
    ValidationError,
)
from pykour.openapi import OpenAPIConfig
from pykour.status_code import StatusCodeInfo, status_code
from pykour.header import HeaderInfo, header
from pykour.conditional import ETagInfo, LastModifiedInfo, etag, last_modified

__all__ = [
    "Pykour",
    # Config
    "PykourConfig",
    "load_config",
    "Request",
    "Response",
    "JSONResponse",
    "HTMLResponse",
    "PlainTextResponse",
    "FileResponse",
    "StreamingResponse",
    "EventSourceResponse",
    "ServerSentEvent",
    # WebSocket
    "WebSocket",
    "WebSocketDisconnect",
    "WebSocketState",
    # Middleware
    "BaseMiddleware",
    # Logging
    "get_trace_id",
    # Schema
    "Schema",
    "Field",
    "Path",
    "Query",
    "Body",
    "File",
    "Form",
    "UploadFile",
    "ValidationError",
    # OpenAPI
    "OpenAPIConfig",
    # Status Code
    "status_code",
    "StatusCodeInfo",
    # Header
    "header",
    "HeaderInfo",
    # Conditional requests (ETag/Last-Modified)
    "etag",
    "ETagInfo",
    "last_modified",
    "LastModifiedInfo",
    # Exception handling
    "ExceptionHandler",
    "ExceptionHandlerRegistry",
    # HTTP Exceptions - Base
    "HTTPException",
    # HTTP Exceptions - 4xx Client Errors
    "BadRequestException",
    "UnauthorizedException",
    "PaymentRequiredException",
    "ForbiddenException",
    "NotFoundException",
    "MethodNotAllowedException",
    "NotAcceptableException",
    "ProxyAuthenticationRequiredException",
    "RequestTimeoutException",
    "ConflictException",
    "GoneException",
    "LengthRequiredException",
    "PreconditionFailedException",
    "PayloadTooLargeException",
    "URITooLongException",
    "UnsupportedMediaTypeException",
    "RangeNotSatisfiableException",
    "ExpectationFailedException",
    "ImATeapotException",
    "MisdirectedRequestException",
    "UnprocessableEntityException",
    "LockedException",
    "FailedDependencyException",
    "TooEarlyException",
    "UpgradeRequiredException",
    "PreconditionRequiredException",
    "TooManyRequestsException",
    "RequestHeaderFieldsTooLargeException",
    "UnavailableForLegalReasonsException",
    # HTTP Exceptions - 5xx Server Errors
    "InternalServerErrorException",
    "NotImplementedException",
    "BadGatewayException",
    "ServiceUnavailableException",
    "GatewayTimeoutException",
    "HTTPVersionNotSupportedException",
    "VariantAlsoNegotiatesException",
    "InsufficientStorageException",
    "LoopDetectedException",
    "NotExtendedException",
    "NetworkAuthenticationRequiredException",
]

try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("pykour")
except PackageNotFoundError:
    __version__ = "unknown"
