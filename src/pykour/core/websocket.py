"""WebSocket handling utilities for Pykour."""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from pykour.injection import ParameterInjector
    from pykour.router import Router
    from pykour.types import Receive, Scope, Send
    from pykour.websocket import WebSocket


logger = logging.getLogger("pykour")


async def handle_websocket(
    scope: "Scope",
    receive: "Receive",
    send: "Send",
    router: "Router",
    injector: "ParameterInjector",
) -> None:
    """Handle WebSocket connections.

    Args:
        scope: ASGI WebSocket scope.
        receive: ASGI receive callable.
        send: ASGI send callable.
        router: The router instance for route matching.
        injector: The parameter injector for dependency injection.
    """
    from pykour.websocket import WebSocket, WebSocketDisconnect, WebSocketState

    path = scope.get("path", "/")
    handler, path_params = router.match(path, "WEBSOCKET")

    if handler is None:
        # No WebSocket handler found - close with 4004 (not found)
        await send(
            {
                "type": "websocket.close",
                "code": 4004,
                "reason": "Not Found",
            }
        )
        return

    ws = WebSocket(scope, receive, send, path_params)

    try:
        # Inject parameters (WebSocket instance and path params)
        kwargs = await inject_websocket_params(handler, ws, path_params, injector)

        result = handler(**kwargs)
        if inspect.isawaitable(result):
            await result
    except WebSocketDisconnect:
        pass  # Normal disconnect
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")

        if ws.state != WebSocketState.DISCONNECTED:
            try:
                await ws.close(code=1011, reason="Internal Error")
            except Exception:
                pass  # Connection may already be closed


async def inject_websocket_params(
    handler: Callable[..., Any],
    ws: "WebSocket",
    path_params: dict[str, str],
    injector: "ParameterInjector",
) -> dict[str, Any]:
    """Inject parameters for WebSocket handler.

    Supports:
    - WebSocket instance (ws parameter or by type annotation)
    - Path parameters
    - Service dependencies via Depends()

    Args:
        handler: The WebSocket handler function.
        ws: The WebSocket connection instance.
        path_params: Path parameters extracted from URL.
        injector: The parameter injector for dependency injection.

    Returns:
        Dictionary of keyword arguments for the handler.
    """
    from typing import get_type_hints

    from pykour.di import Depends as DIDepends
    from pykour.schema.fields import Path as PathParam
    from pykour.schema.parser import coerce_path_param
    from pykour.websocket import WebSocket as WebSocketClass

    try:
        hints = get_type_hints(handler)
    except Exception:
        hints = {}

    sig = inspect.signature(handler)
    kwargs: dict[str, Any] = {}

    for param_name, param in sig.parameters.items():
        param_type = hints.get(param_name, Any)
        default = param.default

        # WebSocket instance injection (by type or by name)
        if param_type is WebSocketClass or param_name == "ws":
            kwargs[param_name] = ws

        # Service dependency injection
        elif isinstance(default, DIDepends):
            service = injector.inject_service_depends(param_name, param_type, default)
            kwargs[param_name] = service

        # Path parameter with explicit marker
        elif isinstance(default, PathParam):
            kwargs[param_name] = injector.inject_path_param(
                param_name, param_type, default, path_params
            )

        # Path parameter by convention (name matches)
        elif param_name in path_params:
            kwargs[param_name] = coerce_path_param(
                path_params[param_name], param_name, param_type
            )

        # Default value
        elif param.default is not inspect.Parameter.empty:
            kwargs[param_name] = param.default

    return kwargs
