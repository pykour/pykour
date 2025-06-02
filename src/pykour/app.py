import os
import importlib.util
from pathlib import Path
from .types import Scope, Receive, Send
from .request import Request
from .response import Response


class ASGIApp:
    def __init__(self, prefix: str = "", base_path: str = "./routers") -> None:
        self.prefix = prefix
        self.base_path = Path(base_path)

    def resolve_handler_path(self, method: str, path: str) -> Path | None:
        """Resolve request path to handler file path."""
        # Remove prefix from path
        if path.startswith(self.prefix):
            path = path[len(self.prefix):]
        
        # Remove leading slash and split path
        path_parts = path.strip("/").split("/") if path.strip("/") else []
        
        # Convert HTTP method to lowercase for file name
        method_lower = method.lower()
        
        # Build file path
        if path_parts:
            # e.g., /users -> ./routers/users/get.py
            handler_path = self.base_path / "/".join(path_parts) / f"{method_lower}.py"
        else:
            # Root path -> ./routers/get.py
            handler_path = self.base_path / f"{method_lower}.py"
        
        return handler_path if handler_path.exists() else None

    def load_handler(self, handler_path: Path):
        """Dynamically load handler module from file path."""
        spec = importlib.util.spec_from_file_location("handler", handler_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {handler_path}")
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Look for a handler function in the module
        if hasattr(module, "handler"):
            return module.handler
        elif hasattr(module, "handle"):
            return module.handle
        else:
            raise AttributeError(f"No handler function found in {handler_path}")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        
        request = Request(scope, receive)
        
        # Resolve handler path
        handler_path = self.resolve_handler_path(request.method, request.path)
        
        if handler_path is None:
            # Send 404 response
            response = Response("Not Found", status=404)
            await response.send(send)
            return
        
        try:
            # Create response object with method-based default status
            response = Response(method=request.method)
            
            # Load and execute handler
            handler = self.load_handler(handler_path)
            result = await handler(request, response)
            
            # If handler returns a value, use it as the response body
            if result is not None:
                response._body = result
            
            # Send response
            await response.send(send)
        except Exception as e:
            # Send 500 response on error
            response = Response(f"Internal Server Error: {str(e)}", status=500)
            await response.send(send)
