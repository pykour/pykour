"""Route file generator for the generate route command."""

from __future__ import annotations

import re
from pathlib import Path

from pykour.generators.templates import (
    SIMPLE_HANDLER_TEMPLATE,
    SIMPLE_ROUTE_FILE_TEMPLATE,
)

VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}
CRUD_METHODS = ["GET", "POST", "PUT", "DELETE"]


def parse_methods(method_arg: str) -> list[str]:
    """Parse method argument into list of HTTP methods.

    Args:
        method_arg: Method specification (e.g., "GET", "GET,POST", "CRUD")

    Returns:
        List of HTTP method names.

    Raises:
        ValueError: If an invalid method is specified.
    """
    method_upper = method_arg.upper()

    if method_upper == "CRUD":
        return CRUD_METHODS

    methods = [m.strip() for m in method_upper.split(",")]

    for method in methods:
        if method not in VALID_METHODS:
            raise ValueError(f"Invalid HTTP method: {method}")

    return methods


class RouteGenerator:
    """Generate route file for specific HTTP methods."""

    def __init__(
        self,
        path: str,
        methods: list[str],
        routes_dir: str = "routes",
    ) -> None:
        """Initialize RouteGenerator.

        Args:
            path: URL path (e.g., "/api/v1/hello")
            methods: List of HTTP methods (e.g., ["GET", "POST"])
            routes_dir: Routes directory (default: "routes")
        """
        self.path = path
        self.methods = methods
        self.routes_dir = Path(routes_dir)

    def generate(self, force: bool = False) -> Path:
        """Generate route file.

        Args:
            force: Overwrite existing file if True.

        Returns:
            Path to created file.

        Raises:
            FileExistsError: If file exists and force is False.
        """
        route_dir = self._path_to_route_dir()
        route_dir.mkdir(parents=True, exist_ok=True)

        route_file = route_dir / "route.py"
        if route_file.exists() and not force:
            raise FileExistsError(f"File already exists: {route_file}")

        content = self._generate_content()
        route_file.write_text(content)

        return route_file

    def _path_to_route_dir(self) -> Path:
        """Convert URL path to route directory.

        Converts:
            /api/v1/hello -> routes/api/v1/hello
            /api/users/{id} -> routes/api/users/[id]
        """
        clean_path = self.path.strip("/")
        # {param} -> [param] conversion
        clean_path = re.sub(r"\{(\w+)\}", r"[\1]", clean_path)
        return self.routes_dir / clean_path

    def _generate_content(self) -> str:
        """Generate route file content."""
        handlers = []
        for method in self.methods:
            handler = self._generate_handler(method.lower())
            handlers.append(handler)

        return SIMPLE_ROUTE_FILE_TEMPLATE.format(
            path=self.path,
            handlers="\n\n".join(handlers),
        )

    def _generate_handler(self, method: str) -> str:
        """Generate single handler function."""
        return SIMPLE_HANDLER_TEMPLATE.format(
            method_lower=method,
            method_upper=method.upper(),
            path=self.path,
        )
