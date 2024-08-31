from __future__ import annotations
from http import HTTPStatus
from typing import Any, Callable, Dict, Union, List, Tuple


class Route:
    def __init__(self, path: str, method: str, handler: Any):
        self.path = path
        self.method = method
        self.handler = handler
        self.path_params: Dict[str, str] = {}

    def set_path_params(self, path_params: Dict[str, str]):
        self.path_params = path_params


class Node:
    def __init__(self, part: str, is_wild: bool = False):
        self.part = part
        self.children: list[Node] = []
        self.is_wild = is_wild
        self.route: Union[Route, None] = None

    def insert(self, pattern: str, route: Route):
        parts = pattern.strip("/").split("/")

        node = self
        for part in parts:
            child = node.match_child(part)
            if not child:
                child = Node(
                    part,
                    part.startswith(":") or part.startswith("*") or part.startswith("{"),
                )
                node.children.append(child)
            node = child

        node.route = route

    def search(self, path: str):
        parts = path.strip("/").split("/")
        path_params = {}

        node = self
        for part in parts:
            child = node.match_child(part)
            if not child:
                return None, {}
            if child.is_wild:
                var_name = child.part.lstrip(":*{").rstrip("}")
                path_params[var_name] = part
            node = child

        # route = node.route_map.get(method)
        return node.route, path_params

    def match_child(self, part: str):
        for child in self.children:
            if child.part == part and not child.is_wild:
                return child
        for child in self.children:
            if child.is_wild:
                return child
        return None


class Router:
    SUPPORTED_METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]

    def __init__(self, prefix: str = ""):
        """Router class.

        Args:
            prefix: Prefix for the router.
        """
        self.roots: dict[str, Node] = {}
        self.prefix = prefix.rstrip("/")

    def __str__(self):
        routes: List[str] = []

        def traverse(node, prefix=""):
            for child in node.children:
                new_prefix = f"{prefix}/{child.part}".strip("/")
                route = child.route
                if route:
                    handler_name = route.handler[0].__name__
                    route_description = f"{method} /{new_prefix} -> {handler_name}()"
                    routes.append(route_description)
                traverse(child, new_prefix)

        for method, root in self.roots.items():
            traverse(root)
        return "\n".join(routes)

    def __repr__(self):
        return "Router(prefix='{}')".format(self.prefix)

    def get(self, path: str, status_code: HTTPStatus = HTTPStatus.OK) -> Callable:
        """Decorator for GET method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="GET", status_code=status_code)

    def post(self, path: str, status_code: HTTPStatus = HTTPStatus.CREATED) -> Callable:
        """Decorator for POST method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="POST", status_code=status_code)

    def put(self, path: str, status_code: HTTPStatus = HTTPStatus.OK) -> Callable:
        """Decorator for PUT method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="PUT", status_code=status_code)

    def delete(self, path: str, status_code: HTTPStatus = HTTPStatus.NO_CONTENT) -> Callable:
        """Decorator for DELETE method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="DELETE", status_code=status_code)

    def patch(self, path: str, status_code: HTTPStatus = HTTPStatus.OK) -> Callable:
        """Decorator for PATCH method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="PATCH", status_code=status_code)

    def options(self, path: str, status_code: HTTPStatus = HTTPStatus.OK) -> Callable:
        """Decorator for OPTIONS method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="OPTIONS", status_code=status_code)

    def head(self, path: str, status_code: HTTPStatus = HTTPStatus.OK) -> Callable:
        """Decorator for HEAD method.

        Args:
            path: URL path.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """
        return self.route(path=path, method="HEAD", status_code=status_code)

    def route(self, path: str, method: str = "GET", status_code: Union[HTTPStatus, int] = HTTPStatus.OK) -> Callable:
        """Decorator for route.

        Args:
            path: URL path.
            method: HTTP method.
            status_code: HTTP status code.
        Returns:
            Route decorator.
        """

        if method not in self.SUPPORTED_METHODS:
            raise ValueError(f"Unsupported HTTP method: {method}")

        def decorator(func):
            self.add_route(path, method, (func, status_code))
            return func

        return decorator

    def add_router(self, router: Router, prefix: str = ""):
        """Add router.

        Args:
            router: Router instance.
            prefix: Prefix for the router.
        """

        def traverse(node, prefix=""):
            for child in node.children:
                new_prefix = f"{prefix}/{child.part}".rstrip("/")
                route = child.route
                if route:
                    self.add_route(new_prefix, method, route.handler)
                traverse(child, new_prefix)

        for method, root in router.roots.items():
            traverse(root, prefix=prefix)

    def add_route(self, path: str, method: str, handler: Any):
        """Add route.

        Args:
            path: URL path.
            method: HTTP method.
            handler: Route handler.
        """
        if self.prefix:
            full_path = f"/{self.prefix}{path}"
        else:
            full_path = path
        route = Route(full_path, method, handler)
        if method not in self.roots:
            self.roots[method] = Node("")
        self.roots[method].insert(full_path, route)

    def get_route(self, path: str, method: str) -> Union[Route, None]:
        """Get route.

        Args:
            path: URL path.
            method: HTTP method.
        """
        if method in self.roots:
            route, path_params = self.roots[method].search(path)
            if route:
                route.set_path_params(path_params)
            return route
        return None

    def get_openapi_routes(self) -> List[Tuple[str, Tuple[str, Any]]]:
        routes = []

        for method in self.roots:
            root = self.roots[method]

            def traverse(node, prefix=""):
                for child in node.children:
                    new_prefix = f"{prefix}/{child.part}".rstrip("/")
                    if new_prefix == "":
                        new_prefix = "/"
                    route = child.route
                    if route:
                        routes.append((new_prefix, (method, route.handler)))
                    traverse(child, new_prefix)

            traverse(root)

        return routes

    def get_allowed_methods(self, path: str) -> List[str]:
        """Get allowed HTTP methods for the specified path.

        Args:
            path: URL path.

        Returns:
            List of allowed HTTP methods.
        """
        allowed_methods = []
        http_methods = [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "PATCH",
            "OPTIONS",
            "HEAD",
        ]

        for method in http_methods:
            if self.get_route(path, method):
                allowed_methods.append(method)

        return allowed_methods

    def exists(self, path: str, method: str) -> bool:
        """Check if route exists.

        Args:
            path: URL path.
            method: HTTP method.
        Returns:
            True if route exists, False otherwise.
        """
        return self.get_route(path, method) is not None
