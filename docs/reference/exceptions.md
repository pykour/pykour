---
title: HTTP Exceptions
parent: Reference
nav_order: 1
---

# HTTP Exceptions

Pykour provides a comprehensive set of HTTP exception classes in `pykour.exceptions`. All exceptions inherit from the base `HTTPException` class and can be raised in route handlers or middleware to return appropriate HTTP error responses.

## Base Class

### `HTTPException`

The base class for all HTTP exceptions. You can use it directly or subclass it for custom error types.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `detail` | `str \| None` | Class default | Error message included in the response body |
| `status_code` | `int \| None` | Class default | HTTP status code |
| `headers` | `dict[str, str] \| None` | `{}` | Additional headers to include in the response |

**Example:**

```python
from pykour.exceptions import HTTPException

# Direct usage with custom status code
raise HTTPException(
    detail="Resource moved",
    status_code=301,
    headers={"Location": "/new-path"},
)

# Creating a custom exception class
class ItemNotFoundException(HTTPException):
    status_code = 404
    detail = "Item not found"
```

## Basic Usage

```python
from pykour.exceptions import NotFoundException, BadRequestException

async def get(id: int = Path()):
    user = await find_user(id)
    if user is None:
        raise NotFoundException(detail="User not found")
    return user

async def post(data: UserSchema = Body()):
    if await user_exists(data.email):
        raise BadRequestException(detail="Email already registered")
    return await create_user(data)
```

## 4xx Client Error Exceptions

Client error responses indicate that the request contains bad syntax or cannot be fulfilled.

| Status | Exception Class | Default Message | Typical Use Case |
|--------|----------------|-----------------|------------------|
| 400 | `BadRequestException` | Bad Request | Invalid request syntax or parameters |
| 401 | `UnauthorizedException` | Unauthorized | Missing or invalid authentication credentials |
| 402 | `PaymentRequiredException` | Payment Required | Payment is required to access the resource |
| 403 | `ForbiddenException` | Forbidden | Authenticated but not authorized for this action |
| 404 | `NotFoundException` | Not Found | Resource does not exist |
| 405 | `MethodNotAllowedException` | Method Not Allowed | HTTP method not supported for this endpoint |
| 406 | `NotAcceptableException` | Not Acceptable | Cannot produce response matching Accept headers |
| 407 | `ProxyAuthenticationRequiredException` | Proxy Authentication Required | Proxy authentication needed |
| 408 | `RequestTimeoutException` | Request Timeout | Client took too long to send the request |
| 409 | `ConflictException` | Conflict | Request conflicts with current resource state |
| 410 | `GoneException` | Gone | Resource permanently removed |
| 411 | `LengthRequiredException` | Length Required | Content-Length header is required |
| 412 | `PreconditionFailedException` | Precondition Failed | Precondition in request headers evaluated to false |
| 413 | `PayloadTooLargeException` | Payload Too Large | Request body exceeds server limits |
| 414 | `URITooLongException` | URI Too Long | Request URI exceeds server limits |
| 415 | `UnsupportedMediaTypeException` | Unsupported Media Type | Request content type is not supported |
| 416 | `RangeNotSatisfiableException` | Range Not Satisfiable | Range header cannot be fulfilled |
| 417 | `ExpectationFailedException` | Expectation Failed | Expect header cannot be met |
| 418 | `ImATeapotException` | I'm a teapot | Server refuses to brew coffee with a teapot (RFC 2324) |
| 421 | `MisdirectedRequestException` | Misdirected Request | Request directed at wrong server |
| 422 | `UnprocessableEntityException` | Unprocessable Entity | Valid syntax but semantically invalid content |
| 423 | `LockedException` | Locked | Resource is locked (WebDAV) |
| 424 | `FailedDependencyException` | Failed Dependency | Failed due to a previous request failure (WebDAV) |
| 425 | `TooEarlyException` | Too Early | Server unwilling to process potentially replayed request |
| 426 | `UpgradeRequiredException` | Upgrade Required | Client must switch to a different protocol |
| 428 | `PreconditionRequiredException` | Precondition Required | Request must be conditional |
| 429 | `TooManyRequestsException` | Too Many Requests | Rate limit exceeded |
| 431 | `RequestHeaderFieldsTooLargeException` | Request Header Fields Too Large | Header fields exceed server limits |
| 451 | `UnavailableForLegalReasonsException` | Unavailable For Legal Reasons | Resource blocked for legal reasons |

### Common 4xx Examples

```python
from pykour.exceptions import (
    BadRequestException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ConflictException,
    UnprocessableEntityException,
    TooManyRequestsException,
)

# 400 - Invalid input
raise BadRequestException(detail="Invalid email format")

# 401 - Authentication required
raise UnauthorizedException(detail="Token expired")

# 403 - Insufficient permissions
raise ForbiddenException(detail="Admin access required")

# 404 - Resource not found
raise NotFoundException(detail="User not found")

# 409 - Conflict with existing data
raise ConflictException(detail="Username already taken")

# 422 - Validation error
raise UnprocessableEntityException(detail="Age must be a positive number")

# 429 - Rate limiting
raise TooManyRequestsException(
    detail="Rate limit exceeded. Try again in 60 seconds.",
    headers={"Retry-After": "60"},
)
```

## 5xx Server Error Exceptions

Server error responses indicate that the server failed to fulfill a valid request.

| Status | Exception Class | Default Message | Typical Use Case |
|--------|----------------|-----------------|------------------|
| 500 | `InternalServerErrorException` | Internal Server Error | Unexpected server-side failure |
| 501 | `NotImplementedException` | Not Implemented | Feature or method not implemented |
| 502 | `BadGatewayException` | Bad Gateway | Invalid response from upstream server |
| 503 | `ServiceUnavailableException` | Service Unavailable | Server temporarily unavailable (maintenance/overload) |
| 504 | `GatewayTimeoutException` | Gateway Timeout | Upstream server did not respond in time |
| 505 | `HTTPVersionNotSupportedException` | HTTP Version Not Supported | HTTP version in request not supported |
| 506 | `VariantAlsoNegotiatesException` | Variant Also Negotiates | Internal server configuration error |
| 507 | `InsufficientStorageException` | Insufficient Storage | Server cannot store the representation (WebDAV) |
| 508 | `LoopDetectedException` | Loop Detected | Infinite loop detected during request processing |
| 510 | `NotExtendedException` | Not Extended | Further extensions required to fulfill request |
| 511 | `NetworkAuthenticationRequiredException` | Network Authentication Required | Network-level authentication needed |

### Common 5xx Examples

```python
from pykour.exceptions import (
    InternalServerErrorException,
    NotImplementedException,
    ServiceUnavailableException,
    GatewayTimeoutException,
)

# 500 - Unexpected error
raise InternalServerErrorException(detail="Database connection lost")

# 501 - Not yet implemented
raise NotImplementedException(detail="CSV export is not yet available")

# 503 - Service down for maintenance
raise ServiceUnavailableException(
    detail="Service under maintenance",
    headers={"Retry-After": "3600"},
)

# 504 - External service timeout
raise GatewayTimeoutException(detail="Payment provider did not respond")
```

## Custom Exception Classes

You can create custom exceptions by subclassing any built-in exception class:

```python
from pykour.exceptions import NotFoundException, HTTPException

# Simple custom exception with fixed message
class UserNotFoundException(NotFoundException):
    detail = "User not found"

# Custom exception with a non-standard status code
class CustomException(HTTPException):
    status_code = 499
    detail = "Client Closed Request"

# Usage
raise UserNotFoundException()  # 404 with "User not found"
raise CustomException()        # 499 with "Client Closed Request"
```

## Exception Handling in Middleware

Exceptions raised in route handlers are automatically caught and converted to JSON error responses. You can also handle exceptions in custom middleware:

```python
from pykour import Pykour
from pykour.exceptions import HTTPException

app = Pykour()

@app.middleware
async def error_logging_middleware(request, call_next):
    try:
        response = await call_next(request)
        return response
    except HTTPException as exc:
        # Log the error, then re-raise for default handling
        print(f"HTTP {exc.status_code}: {exc.detail}")
        raise
```

---
**See also:** [Exception Handling](../core/exception-handling.md)
[← Back to Home](../index.md)
