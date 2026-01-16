"""Type definitions for ASGI interface."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pykour.request import Request
    from pykour.response import Response

# ASGI Scope types
Scope = MutableMapping[str, Any]

# ASGI Message type
Message = MutableMapping[str, Any]

# ASGI Receive callable
Receive = Callable[[], Awaitable[Message]]

# ASGI Send callable
Send = Callable[[Message], Awaitable[None]]

# ASGI Application callable
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

# Middleware types
CallNext = Callable[["Request"], Awaitable["Response"]]
MiddlewareFunc = Callable[["Request", CallNext], Awaitable["Response"]]
