"""File-based routing for Pykour."""

import importlib.util
import logging
import re
import sys
import warnings
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from pykour.response import Response

# Route handler type
RouteHandler = Callable[..., Awaitable[Response] | Response]

# HTTP methods supported
HTTP_METHODS = ("get", "post", "put", "delete", "patch", "head", "options")

# WebSocket handler name
WEBSOCKET_HANDLER = "websocket"

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Trie node type."""

    STATIC = "static"
    DYNAMIC = "dynamic"
    CATCH_ALL = "catch_all"


@dataclass
class TrieNode:
    """Trie (Prefix Tree) node for route matching.

    Each node represents a path segment and holds references to child nodes.
    Priority: static children > dynamic child > catch-all child
    """

    node_type: NodeType = NodeType.STATIC
    segment: str = ""
    param_name: str | None = None
    handlers: dict[str, RouteHandler] = field(default_factory=dict)
    static_children: dict[str, "TrieNode"] = field(default_factory=dict)
    dynamic_child: "TrieNode | None" = None
    catch_all_child: "TrieNode | None" = None
    path_pattern: str = ""

    def is_endpoint(self) -> bool:
        """Check if this node is a route endpoint."""
        return len(self.handlers) > 0


class Route:
    """Represents a single route."""

    def __init__(
        self,
        path_pattern: str,
        handlers: dict[str, RouteHandler],
        param_names: list[str],
    ) -> None:
        self.path_pattern = path_pattern
        self.handlers = handlers
        self.param_names = param_names
        self._regex = self._compile_pattern(path_pattern)
        # Track if this route has a catch-all segment
        self.is_catch_all = "[..." in path_pattern

    def _compile_pattern(self, pattern: str) -> re.Pattern[str]:
        """Compile path pattern to regex."""
        # Handle root route specially
        if pattern == "/":
            return re.compile(r"^/$")

        # Build regex for non-root routes
        regex_pattern = "^"
        for segment in pattern.split("/"):
            if segment.startswith("[...") and segment.endswith("]"):
                # Catch-all segment: match one or more path segments
                regex_pattern += r"/(.+)"
            elif segment.startswith("[") and segment.endswith("]"):
                # Dynamic segment: match any non-slash characters
                regex_pattern += r"/([^/]+)"
            elif segment:
                regex_pattern += "/" + re.escape(segment)
        regex_pattern += "$"
        return re.compile(regex_pattern)

    def match(self, path: str) -> dict[str, str] | None:
        """Match path and extract parameters. Returns None if no match."""
        match = self._regex.match(path)
        if match:
            return dict(zip(self.param_names, match.groups(), strict=False))
        return None


class Router:
    """File-based router that discovers routes from directory structure.

    Uses a Trie (prefix tree) for O(path_depth) route matching instead of
    O(route_count) linear search.
    """

    def __init__(self, routes_dir: str | Path) -> None:
        self.routes_dir = Path(routes_dir)
        self._root = TrieNode()
        self._routes_cache: list[Route] | None = None
        self._discover_routes()

    @property
    def routes(self) -> list[Route]:
        """Get list of all routes (for backward compatibility).

        This property collects routes from the Trie structure.
        """
        if self._routes_cache is None:
            self._routes_cache = self._collect_routes()
        return self._routes_cache

    def _collect_routes(self) -> list[Route]:
        """Collect all routes from Trie into a list."""
        routes: list[Route] = []
        self._collect_routes_recursive(self._root, [], [], routes)

        # Sort routes by priority for backward compatibility
        def route_priority(route: Route) -> tuple[int, int, int]:
            is_catch_all = 1 if route.is_catch_all else 0
            param_count = route.path_pattern.count("[")
            specificity = -len(route.path_pattern)
            return (is_catch_all, param_count, specificity)

        routes.sort(key=route_priority)
        return routes

    def _collect_routes_recursive(
        self,
        node: TrieNode,
        path_parts: list[str],
        param_names: list[str],
        routes: list[Route],
    ) -> None:
        """Recursively collect routes from Trie nodes."""
        if node.is_endpoint():
            path_pattern = "/" + "/".join(path_parts) if path_parts else "/"
            routes.append(Route(path_pattern, node.handlers.copy(), param_names.copy()))

        # Visit static children
        for segment, child in node.static_children.items():
            self._collect_routes_recursive(
                child, [*path_parts, segment], param_names, routes
            )

        # Visit dynamic child
        if node.dynamic_child:
            child = node.dynamic_child
            self._collect_routes_recursive(
                child,
                [*path_parts, f"[{child.param_name}]"],
                [*param_names, child.param_name or ""],
                routes,
            )

        # Visit catch-all child
        if node.catch_all_child:
            child = node.catch_all_child
            self._collect_routes_recursive(
                child,
                [*path_parts, f"[...{child.param_name}]"],
                [*param_names, child.param_name or ""],
                routes,
            )

    def _discover_routes(self) -> None:
        """Discover and register all routes from the routes directory."""
        if not self.routes_dir.exists():
            warnings.warn(
                f"Routes directory '{self.routes_dir}' does not exist. "
                "No routes will be registered.",
                UserWarning,
                stacklevel=3,
            )
            return

        for route_file in self.routes_dir.rglob("route.py"):
            self._register_route(route_file)

    def _register_route(self, route_file: Path) -> None:
        """Register handlers from a route.py file."""
        # Convert file path to URL path
        relative_path = route_file.parent.relative_to(self.routes_dir)
        path_parts = list(relative_path.parts)

        # Build path pattern from path parts
        path_pattern = "/" + "/".join(path_parts) if path_parts else "/"

        # Load module and extract handlers
        handlers = self._load_handlers(route_file)
        if handlers:
            self._insert(path_pattern, handlers)

    def _insert(self, path_pattern: str, handlers: dict[str, RouteHandler]) -> None:
        """Insert a route into the Trie.

        Args:
            path_pattern: Path pattern (e.g., "/api/users/[id]")
            handlers: HTTP method -> handler mapping
        """
        node = self._root

        # Handle root route specially
        if path_pattern == "/":
            node.handlers.update(handlers)
            node.path_pattern = "/"
            return

        # Split path into segments
        segments = [s for s in path_pattern.split("/") if s]

        for segment in segments:
            if segment.startswith("[...") and segment.endswith("]"):
                # Catch-all segment
                param_name = segment[4:-1]
                if node.catch_all_child is None:
                    node.catch_all_child = TrieNode(
                        node_type=NodeType.CATCH_ALL,
                        segment=segment,
                        param_name=param_name,
                    )
                node = node.catch_all_child
                # Catch-all consumes all remaining segments
                break
            elif segment.startswith("[") and segment.endswith("]"):
                # Dynamic segment
                param_name = segment[1:-1]
                if node.dynamic_child is None:
                    node.dynamic_child = TrieNode(
                        node_type=NodeType.DYNAMIC,
                        segment=segment,
                        param_name=param_name,
                    )
                node = node.dynamic_child
            else:
                # Static segment
                if segment not in node.static_children:
                    node.static_children[segment] = TrieNode(
                        node_type=NodeType.STATIC,
                        segment=segment,
                    )
                node = node.static_children[segment]

        # Register handlers at the endpoint
        node.handlers.update(handlers)
        node.path_pattern = path_pattern

    def register_route(
        self,
        path_pattern: str,
        handlers: dict[str, RouteHandler],
    ) -> None:
        """Register a route programmatically.

        This is the public API for dynamically adding routes without
        creating route.py files.

        Args:
            path_pattern: URL pattern (e.g., "/api/users", "/api/users/[id]").
            handlers: Dict mapping HTTP methods to handler functions.
                Keys should be uppercase (e.g., "GET", "POST").

        Example:
            async def list_users(request):
                return JSONResponse({"users": []})

            async def create_user(request):
                return JSONResponse({"created": True}, status_code=201)

            router.register_route("/api/users", {
                "GET": list_users,
                "POST": create_user,
            })
        """
        self._insert(path_pattern, handlers)
        # Invalidate routes cache
        self._routes_cache = None

    def _load_handlers(self, route_file: Path) -> dict[str, RouteHandler]:
        """Load HTTP method handlers from a route.py file."""
        # Generate unique module name from file path to avoid conflicts
        module_name = f"pykour.routes.{route_file.as_posix().replace('/', '.').replace('.py', '')}"

        spec = importlib.util.spec_from_file_location(module_name, route_file)
        if spec is None or spec.loader is None:
            return {}

        module = importlib.util.module_from_spec(spec)

        # Register module in sys.modules before execution
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
        except SyntaxError as e:
            logger.error(
                "Syntax error in route file '%s': %s (line %d)",
                route_file,
                e.msg,
                e.lineno or 0,
            )
            del sys.modules[module_name]
            return {}
        except ImportError as e:
            logger.error(
                "Import error in route file '%s': %s",
                route_file,
                e,
            )
            del sys.modules[module_name]
            return {}
        except (RuntimeError, TypeError, ValueError, AttributeError) as e:
            logger.error(
                "Failed to load route file '%s': %s",
                route_file,
                e,
            )
            del sys.modules[module_name]
            return {}
        except Exception as e:
            logger.warning(
                "Unexpected error loading route file '%s': %s",
                route_file,
                e,
            )
            del sys.modules[module_name]
            return {}

        handlers: dict[str, RouteHandler] = {}

        # Load HTTP method handlers
        for method in HTTP_METHODS:
            handler = getattr(module, method, None)
            if callable(handler):
                handlers[method.upper()] = handler

        # Load WebSocket handler
        ws_handler = getattr(module, WEBSOCKET_HANDLER, None)
        if callable(ws_handler):
            handlers["WEBSOCKET"] = ws_handler

        return handlers

    def match(
        self, path: str, method: str
    ) -> tuple[RouteHandler | None, dict[str, str]]:
        """Find matching route and extract path parameters using Trie.

        Uses backtracking to ensure priority: static > dynamic > catch-all.

        Returns:
            Tuple of (handler, path_params). Handler is None if no match.
        """
        # Normalize path
        path = self._normalize_path(path)

        # Handle root route
        if path == "/":
            handler = self._root.handlers.get(method.upper())
            return handler, {}

        segments = [s for s in path.split("/") if s]
        params: dict[str, str] = {}

        handler, matched_params = self._match_recursive(
            self._root, segments, 0, params, method.upper()
        )
        return handler, matched_params

    def _normalize_path(self, path: str) -> str:
        """Normalize path by removing trailing slash and collapsing slashes."""
        # Collapse multiple slashes
        while "//" in path:
            path = path.replace("//", "/")
        # Remove trailing slash (except for root)
        if path != "/" and path.endswith("/"):
            path = path[:-1]
        return path

    def _match_recursive(
        self,
        node: TrieNode,
        segments: list[str],
        index: int,
        params: dict[str, str],
        method: str,
    ) -> tuple[RouteHandler | None, dict[str, str]]:
        """Recursively match path segments using backtracking.

        Priority at each level: static > dynamic > catch-all
        """
        # All segments consumed - check if this is an endpoint
        if index == len(segments):
            if node.is_endpoint():
                handler = node.handlers.get(method)
                return handler, params.copy()
            return None, {}

        current_segment = segments[index]

        # Priority 1: Try static match
        if current_segment in node.static_children:
            child = node.static_children[current_segment]
            result = self._match_recursive(child, segments, index + 1, params, method)
            if result[0] is not None:
                return result

        # Priority 2: Try dynamic match
        if node.dynamic_child is not None:
            child = node.dynamic_child
            # Temporarily add parameter
            param_name = child.param_name or ""
            params[param_name] = current_segment
            result = self._match_recursive(child, segments, index + 1, params, method)
            if result[0] is not None:
                return result
            # Backtrack: remove parameter
            del params[param_name]

        # Priority 3: Try catch-all match
        if node.catch_all_child is not None:
            child = node.catch_all_child
            # Catch-all captures all remaining segments
            remaining = "/".join(segments[index:])
            param_name = child.param_name or ""
            params[param_name] = remaining
            if child.is_endpoint():
                handler = child.handlers.get(method)
                if handler is not None:
                    return handler, params.copy()
            del params[param_name]

        return None, {}

    def get_allowed_methods(self, path: str) -> list[str]:
        """Get list of allowed methods for a path.

        Note: HEAD is automatically allowed when GET is available,
        even if no explicit HEAD handler is defined.
        """
        path = self._normalize_path(path)

        # Handle root route
        if path == "/":
            if self._root.is_endpoint():
                methods = list(self._root.handlers.keys())
                if "GET" in methods and "HEAD" not in methods:
                    methods.append("HEAD")
                return methods
            return []

        segments = [s for s in path.split("/") if s]
        node = self._find_matching_node(self._root, segments, 0)

        if node is not None and node.is_endpoint():
            methods = list(node.handlers.keys())
            if "GET" in methods and "HEAD" not in methods:
                methods.append("HEAD")
            return methods
        return []

    def _find_matching_node(
        self,
        node: TrieNode,
        segments: list[str],
        index: int,
    ) -> TrieNode | None:
        """Find the matching Trie node for a path (without method check)."""
        if index == len(segments):
            return node if node.is_endpoint() else None

        current_segment = segments[index]

        # Priority 1: Static match
        if current_segment in node.static_children:
            result = self._find_matching_node(
                node.static_children[current_segment], segments, index + 1
            )
            if result is not None:
                return result

        # Priority 2: Dynamic match
        if node.dynamic_child is not None:
            result = self._find_matching_node(node.dynamic_child, segments, index + 1)
            if result is not None:
                return result

        # Priority 3: Catch-all match
        if node.catch_all_child is not None and node.catch_all_child.is_endpoint():
            return node.catch_all_child

        return None
