"""OpenAPI documentation routes."""

from typing import TYPE_CHECKING, Any

from pykour.openapi.config import OpenAPIConfig
from pykour.openapi.generator import OpenAPIGenerator
from pykour.openapi.ui import get_redoc_html, get_swagger_ui_html
from pykour.response import HTMLResponse, JSONResponse, Response
from pykour.types import Receive, Scope, Send

if TYPE_CHECKING:
    from pykour.application import Pykour


class OpenAPIRouteHandler:
    """Handler for OpenAPI documentation routes.

    This class handles requests to OpenAPI endpoints:
    - /openapi.json - Returns the OpenAPI schema as JSON
    - /docs - Returns Swagger UI HTML
    - /redoc - Returns ReDoc HTML
    """

    def __init__(
        self,
        app: "Pykour",
        config: OpenAPIConfig,
    ) -> None:
        """Initialize OpenAPI route handler.

        Args:
            app: Pykour application instance.
            config: OpenAPI configuration.
        """
        self._app = app
        self._config = config
        self._openapi_schema: dict[str, Any] | None = None

    def get_openapi_schema(self) -> dict[str, Any]:
        """Get or generate the OpenAPI schema.

        The schema is cached after first generation.

        Returns:
            OpenAPI document dictionary.
        """
        if self._openapi_schema is None:
            generator = OpenAPIGenerator(self._app._router, self._config)
            self._openapi_schema = generator.generate()
        return self._openapi_schema

    def matches(self, path: str) -> bool:
        """Check if the path matches any OpenAPI route.

        Args:
            path: Request path.

        Returns:
            True if path matches an OpenAPI route.
        """
        return path in (
            self._config.openapi_url,
            self._config.docs_url,
            self._config.redoc_url,
        )

    async def handle(self, scope: Scope, receive: Receive, send: Send) -> bool:
        """Handle OpenAPI route request.

        Args:
            scope: ASGI scope.
            receive: ASGI receive callable.
            send: ASGI send callable.

        Returns:
            True if the request was handled, False otherwise.
        """
        path = scope.get("path", "/")
        method = scope.get("method", "GET")

        # Only handle GET requests for documentation
        if method != "GET":
            return False

        response: Response | None = None

        if path == self._config.openapi_url:
            response = self._handle_openapi_json()
        elif path == self._config.docs_url:
            response = self._handle_swagger_ui()
        elif path == self._config.redoc_url:
            response = self._handle_redoc()

        if response is not None:
            await response(scope, receive, send)
            return True

        return False

    def _handle_openapi_json(self) -> JSONResponse:
        """Handle /openapi.json request."""
        schema = self.get_openapi_schema()
        return JSONResponse(schema)

    def _handle_swagger_ui(self) -> HTMLResponse:
        """Handle /docs request."""
        openapi_url = self._config.openapi_url or "/openapi.json"
        html = get_swagger_ui_html(
            openapi_url=openapi_url,
            title=self._config.title,
        )
        return HTMLResponse(html)

    def _handle_redoc(self) -> HTMLResponse:
        """Handle /redoc request."""
        openapi_url = self._config.openapi_url or "/openapi.json"
        html = get_redoc_html(
            openapi_url=openapi_url,
            title=self._config.title,
        )
        return HTMLResponse(html)


def setup_openapi(app: "Pykour", config: OpenAPIConfig) -> OpenAPIRouteHandler:
    """Set up OpenAPI documentation routes for a Pykour application.

    Args:
        app: Pykour application instance.
        config: OpenAPI configuration.

    Returns:
        OpenAPI route handler instance.
    """
    return OpenAPIRouteHandler(app, config)
