"""HTTP exception classes for Pykour.

This module provides a hierarchy of HTTP exceptions that can be raised
in route handlers and automatically converted to appropriate HTTP responses.

Example:
    from pykour.exceptions import NotFoundException, BadRequestException

    @app.get("/items/{id}")
    async def get_item(id: int):
        item = await find_item(id)
        if not item:
            raise NotFoundException(detail=f"Item {id} not found")
        return item

    @app.post("/items")
    async def create_item(data: ItemCreate):
        if not data.name:
            raise BadRequestException(detail="Name is required")
        return await create_item_in_db(data)
"""

from __future__ import annotations


class HTTPException(Exception):
    """Base HTTP exception class.

    All HTTP exceptions inherit from this class. Subclasses should define
    class-level `status_code` and `detail` attributes as defaults.

    Args:
        detail: Error message to include in response. Defaults to class-level detail.
        status_code: HTTP status code. Defaults to class-level status_code.
        headers: Additional headers to include in response.

    Example:
        # Using a predefined exception
        raise NotFoundException(detail="User not found")

        # Creating a custom exception with headers
        raise HTTPException(
            detail="Resource moved",
            status_code=301,
            headers={"Location": "/new-path"},
        )

        # Creating a custom exception class
        class ItemNotFoundException(NotFoundException):
            detail = "Item not found"
    """

    status_code: int = 500
    detail: str = "Internal Server Error"

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize HTTP exception.

        Args:
            detail: Error message. Uses class default if not provided.
            status_code: HTTP status code. Uses class default if not provided.
            headers: Additional response headers.
        """
        self.detail = detail if detail is not None else self.__class__.detail
        self.status_code = (
            status_code if status_code is not None else self.__class__.status_code
        )
        self.headers = headers or {}
        super().__init__(self.detail)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(status_code={self.status_code}, detail={self.detail!r})"


# 4xx Client Error Exceptions


class BadRequestException(HTTPException):
    """400 Bad Request.

    The server cannot or will not process the request due to something
    that is perceived to be a client error.
    """

    status_code = 400
    detail = "Bad Request"


class UnauthorizedException(HTTPException):
    """401 Unauthorized.

    The request requires user authentication. The client must authenticate
    itself to get the requested response.
    """

    status_code = 401
    detail = "Unauthorized"


class PaymentRequiredException(HTTPException):
    """402 Payment Required.

    Reserved for future use. The original intention was for digital
    payment systems.
    """

    status_code = 402
    detail = "Payment Required"


class ForbiddenException(HTTPException):
    """403 Forbidden.

    The server understood the request but refuses to authorize it.
    Unlike 401, authenticating will not help.
    """

    status_code = 403
    detail = "Forbidden"


class NotFoundException(HTTPException):
    """404 Not Found.

    The server cannot find the requested resource. This can also mean
    the endpoint is valid but the resource itself does not exist.
    """

    status_code = 404
    detail = "Not Found"


class MethodNotAllowedException(HTTPException):
    """405 Method Not Allowed.

    The request method is known by the server but has been disabled
    and cannot be used for the target resource.
    """

    status_code = 405
    detail = "Method Not Allowed"


class NotAcceptableException(HTTPException):
    """406 Not Acceptable.

    The server cannot produce a response matching the list of acceptable
    values defined in the request's proactive content negotiation headers.
    """

    status_code = 406
    detail = "Not Acceptable"


class ProxyAuthenticationRequiredException(HTTPException):
    """407 Proxy Authentication Required.

    The client must first authenticate itself with the proxy.
    """

    status_code = 407
    detail = "Proxy Authentication Required"


class RequestTimeoutException(HTTPException):
    """408 Request Timeout.

    The server would like to shut down this unused connection.
    """

    status_code = 408
    detail = "Request Timeout"


class ConflictException(HTTPException):
    """409 Conflict.

    The request could not be completed due to a conflict with the
    current state of the target resource.
    """

    status_code = 409
    detail = "Conflict"


class GoneException(HTTPException):
    """410 Gone.

    The target resource is no longer available at the origin server
    and this condition is likely to be permanent.
    """

    status_code = 410
    detail = "Gone"


class LengthRequiredException(HTTPException):
    """411 Length Required.

    The server refuses to accept the request without a defined
    Content-Length header.
    """

    status_code = 411
    detail = "Length Required"


class PreconditionFailedException(HTTPException):
    """412 Precondition Failed.

    One or more conditions given in the request header fields evaluated
    to false when tested on the server.
    """

    status_code = 412
    detail = "Precondition Failed"


class PayloadTooLargeException(HTTPException):
    """413 Payload Too Large.

    The request entity is larger than limits defined by server.
    """

    status_code = 413
    detail = "Payload Too Large"


class URITooLongException(HTTPException):
    """414 URI Too Long.

    The URI requested by the client is longer than the server is
    willing to interpret.
    """

    status_code = 414
    detail = "URI Too Long"


class UnsupportedMediaTypeException(HTTPException):
    """415 Unsupported Media Type.

    The media format of the requested data is not supported by the
    server, so the server is rejecting the request.
    """

    status_code = 415
    detail = "Unsupported Media Type"


class RangeNotSatisfiableException(HTTPException):
    """416 Range Not Satisfiable.

    The range specified by the Range header field in the request
    cannot be fulfilled.
    """

    status_code = 416
    detail = "Range Not Satisfiable"


class ExpectationFailedException(HTTPException):
    """417 Expectation Failed.

    The expectation given in the request's Expect header field
    could not be met by at least one of the inbound servers.
    """

    status_code = 417
    detail = "Expectation Failed"


class ImATeapotException(HTTPException):
    """418 I'm a teapot.

    The server refuses the attempt to brew coffee with a teapot.
    """

    status_code = 418
    detail = "I'm a teapot"


class MisdirectedRequestException(HTTPException):
    """421 Misdirected Request.

    The request was directed at a server that is not able to
    produce a response.
    """

    status_code = 421
    detail = "Misdirected Request"


class UnprocessableEntityException(HTTPException):
    """422 Unprocessable Entity.

    The server understands the content type and syntax of the request
    but was unable to process the contained instructions.
    """

    status_code = 422
    detail = "Unprocessable Entity"


class LockedException(HTTPException):
    """423 Locked.

    The resource that is being accessed is locked.
    """

    status_code = 423
    detail = "Locked"


class FailedDependencyException(HTTPException):
    """424 Failed Dependency.

    The request failed due to failure of a previous request.
    """

    status_code = 424
    detail = "Failed Dependency"


class TooEarlyException(HTTPException):
    """425 Too Early.

    The server is unwilling to risk processing a request that might
    be replayed.
    """

    status_code = 425
    detail = "Too Early"


class UpgradeRequiredException(HTTPException):
    """426 Upgrade Required.

    The server refuses to perform the request using the current
    protocol but might be willing to do so after the client upgrades.
    """

    status_code = 426
    detail = "Upgrade Required"


class PreconditionRequiredException(HTTPException):
    """428 Precondition Required.

    The origin server requires the request to be conditional.
    """

    status_code = 428
    detail = "Precondition Required"


class TooManyRequestsException(HTTPException):
    """429 Too Many Requests.

    The user has sent too many requests in a given amount of time.
    """

    status_code = 429
    detail = "Too Many Requests"


class RequestHeaderFieldsTooLargeException(HTTPException):
    """431 Request Header Fields Too Large.

    The server is unwilling to process the request because its header
    fields are too large.
    """

    status_code = 431
    detail = "Request Header Fields Too Large"


class UnavailableForLegalReasonsException(HTTPException):
    """451 Unavailable For Legal Reasons.

    The user agent requested a resource that cannot legally be
    provided.
    """

    status_code = 451
    detail = "Unavailable For Legal Reasons"


# 5xx Server Error Exceptions


class InternalServerErrorException(HTTPException):
    """500 Internal Server Error.

    The server encountered an unexpected condition that prevented it
    from fulfilling the request.
    """

    status_code = 500
    detail = "Internal Server Error"


class NotImplementedException(HTTPException):
    """501 Not Implemented.

    The server does not support the functionality required to fulfill
    the request.
    """

    status_code = 501
    detail = "Not Implemented"


class BadGatewayException(HTTPException):
    """502 Bad Gateway.

    The server, while acting as a gateway or proxy, received an invalid
    response from an inbound server.
    """

    status_code = 502
    detail = "Bad Gateway"


class ServiceUnavailableException(HTTPException):
    """503 Service Unavailable.

    The server is not ready to handle the request. Common causes are
    a server that is down for maintenance or that is overloaded.
    """

    status_code = 503
    detail = "Service Unavailable"


class GatewayTimeoutException(HTTPException):
    """504 Gateway Timeout.

    The server, while acting as a gateway or proxy, did not receive
    a timely response from an upstream server.
    """

    status_code = 504
    detail = "Gateway Timeout"


class HTTPVersionNotSupportedException(HTTPException):
    """505 HTTP Version Not Supported.

    The server does not support the major version of HTTP that was
    used in the request message.
    """

    status_code = 505
    detail = "HTTP Version Not Supported"


class VariantAlsoNegotiatesException(HTTPException):
    """506 Variant Also Negotiates.

    The server has an internal configuration error.
    """

    status_code = 506
    detail = "Variant Also Negotiates"


class InsufficientStorageException(HTTPException):
    """507 Insufficient Storage.

    The server is unable to store the representation needed to
    complete the request.
    """

    status_code = 507
    detail = "Insufficient Storage"


class LoopDetectedException(HTTPException):
    """508 Loop Detected.

    The server detected an infinite loop while processing the request.
    """

    status_code = 508
    detail = "Loop Detected"


class NotExtendedException(HTTPException):
    """510 Not Extended.

    Further extensions to the request are required for the server
    to fulfill it.
    """

    status_code = 510
    detail = "Not Extended"


class NetworkAuthenticationRequiredException(HTTPException):
    """511 Network Authentication Required.

    The client needs to authenticate to gain network access.
    """

    status_code = 511
    detail = "Network Authentication Required"
