from http import HTTPStatus
from typing import Callable, Union, MutableMapping, Any, Awaitable


Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]
HTTPStatusCode = Union[int, HTTPStatus]
