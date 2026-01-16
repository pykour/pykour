"""Parameter injection implementation for Pykour."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Callable

import orjson

from pykour.di import Depends as DIDepends
from pykour.di import ServiceContainer, ServiceNotFoundException
from pykour.injection.body_parsers import DEFAULT_BODY_PARSERS, BodyParser
from pykour.schema.errors import ErrorDetail, ValidationError
from pykour.schema.fields import Body, FieldInfo, Path as PathParam, Query
from pykour.schema.parser import coerce_path_param, coerce_query_param, coerce_value

if TYPE_CHECKING:
    from pykour.db.database import Database
    from pykour.request import Request


def _raise_validation_error(
    loc_type: str,
    param_name: str,
    msg: str,
    error_type: str,
) -> None:
    """Raise a ValidationError with consistent formatting."""
    raise ValidationError(
        [
            ErrorDetail(
                loc=(loc_type, param_name),
                msg=msg,
                type=error_type,
            )
        ]
    )


class ParameterInjector:
    """Handles parameter injection for route handlers.

    Extracts and validates handler parameters from various sources:
    - Path parameters from URL segments
    - Query parameters from query string
    - Body parameters from JSON request body
    - Dependencies from service container

    Example:
        injector = ParameterInjector(services, database, body_parsers)
        kwargs = await injector.inject(handler, request, path_params)
        result = await handler(**kwargs)
    """

    def __init__(
        self,
        services: ServiceContainer,
        database: Database | None = None,
        body_parsers: list[BodyParser] | None = None,
    ) -> None:
        """Initialize the parameter injector.

        Args:
            services: Service container for dependency injection.
            database: Optional database instance for backward compatibility.
            body_parsers: List of body parsers. Defaults to DEFAULT_BODY_PARSERS.
        """
        self._services = services
        self._database = database
        self._body_parsers = body_parsers or DEFAULT_BODY_PARSERS

    def inject_service_depends(
        self,
        param_name: str,
        param_type: type,
        default: DIDepends,
    ) -> Any:
        """Inject service dependency from container.

        Args:
            param_name: Name of the parameter.
            param_type: Expected type of the parameter.
            default: DIDepends marker instance.

        Returns:
            Resolved service instance.

        Raises:
            RuntimeError: If service is not registered.
        """
        from pykour.db.database import Database

        dep_type = default.dependency or param_type

        # Check if it's a callable (factory function)
        if callable(dep_type) and not isinstance(dep_type, type):
            return self._services._call_with_dependencies(dep_type)

        # Try to resolve from service container
        if self._services.is_registered(dep_type):
            return self._services.resolve(dep_type)

        # Fallback: check if it's a Database type for backward compatibility
        if dep_type is Database or (
            isinstance(dep_type, type) and issubclass(dep_type, Database)
        ):
            if self._database is not None:
                return self._database
            raise RuntimeError(
                f"No database configured for parameter '{param_name}'. "
                "Either pass a Database to Pykour() or register it with services."
            )

        raise ServiceNotFoundException(dep_type)

    def inject_path_param(
        self,
        param_name: str,
        param_type: type,
        default: PathParam,
        path_params: dict[str, str],
    ) -> Any:
        """Inject path parameter value.

        Args:
            param_name: Name of the parameter.
            param_type: Expected type of the parameter.
            default: PathParam marker instance.
            path_params: Path parameters from the route.

        Returns:
            Coerced path parameter value.

        Raises:
            ValidationError: If required parameter is missing.
        """
        if param_name in path_params:
            return coerce_path_param(
                path_params[param_name],
                param_name,
                param_type,
            )
        elif default.has_default:
            return default.get_default()
        else:
            _raise_validation_error(
                "path", param_name, "Path parameter required", "value_error.missing"
            )

    async def inject_body_param(
        self,
        param_name: str,
        param_type: type,
        request: Request,
        body_data: dict[str, Any] | None,
    ) -> tuple[Any, dict[str, Any]]:
        """Inject body parameter value.

        Args:
            param_name: Name of the parameter.
            param_type: Expected type of the parameter.
            request: Request instance.
            body_data: Cached body data (may be None).

        Returns:
            Tuple of (injected value, body_data for caching).

        Raises:
            ValidationError: If JSON is malformed or parsing fails.
        """
        if body_data is None:
            try:
                body_data = await request.json()
            except orjson.JSONDecodeError as e:
                raise ValidationError(
                    [
                        ErrorDetail(
                            loc=("body",),
                            msg=f"Malformed JSON: {e}",
                            type="value_error.jsondecode",
                        )
                    ]
                ) from e

        # Try each body parser in order
        for parser in self._body_parsers:
            if parser.can_parse(param_type):
                return parser.parse(param_name, param_type, body_data), body_data

        # No parser found - raise clear error
        type_name = getattr(param_type, "__name__", str(param_type))
        raise ValidationError(
            [
                ErrorDetail(
                    loc=("body", param_name),
                    msg=f"Unsupported body parameter type: {type_name}. "
                    f"Supported types: dict, Schema subclasses, dataclasses, "
                    f"pydantic models, and primitives (int, float, str, bool, list).",
                    type="type_error.unsupported",
                )
            ]
        )

    def inject_query_param(
        self,
        param_name: str,
        param_type: type,
        default: Query | FieldInfo,
        query_params: dict[str, str | list[str]],
    ) -> Any:
        """Inject query parameter value.

        Args:
            param_name: Name of the parameter.
            param_type: Expected type of the parameter.
            default: Query or FieldInfo marker instance.
            query_params: Query parameters from the request.

        Returns:
            Coerced query parameter value.

        Raises:
            ValidationError: If required parameter is missing.
        """
        key = default.alias or param_name

        if key in query_params:
            return coerce_query_param(
                query_params[key],
                param_name,
                param_type,
                default,
            )
        elif default.has_default:
            return default.get_default()
        else:
            _raise_validation_error(
                "query", param_name, "Query parameter required", "value_error.missing"
            )

    def inject_convention_query(
        self,
        param_name: str,
        param_type: type,
        value: Any,
    ) -> Any:
        """Inject convention-based query parameter.

        Args:
            param_name: Name of the parameter.
            param_type: Expected type of the parameter.
            value: Raw value from query string.

        Returns:
            Coerced value.

        Raises:
            ValidationError: If type coercion fails.
        """
        try:
            return coerce_value(value, param_type)
        except (TypeError, ValueError) as e:
            _raise_validation_error("query", param_name, str(e), "type_error")

    async def inject(
        self,
        handler: Callable[..., Any],
        request: Request,
        path_params: dict[str, str],
    ) -> dict[str, Any]:
        """Extract and validate handler parameters.

        Args:
            handler: The route handler function.
            request: The current request.
            path_params: Path parameters from URL matching.

        Returns:
            Dictionary of parameter name to value for calling the handler.

        Raises:
            ValidationError: If required parameters are missing or validation fails.
        """
        try:
            hints = inspect.get_annotations(handler, eval_str=True)
        except (NameError, AttributeError, TypeError):
            hints = {}

        sig = inspect.signature(handler)
        kwargs: dict[str, Any] = {}
        query_params = request.query_params
        body_data: dict[str, Any] | None = None

        for param_name, param in sig.parameters.items():
            if param_name == "request":
                kwargs["request"] = request
                continue

            param_type = hints.get(param_name, str)
            default = param.default

            # Check for Depends (pykour.di)
            if isinstance(default, DIDepends):
                kwargs[param_name] = self.inject_service_depends(
                    param_name, param_type, default
                )

            elif isinstance(default, PathParam):
                kwargs[param_name] = self.inject_path_param(
                    param_name, param_type, default, path_params
                )

            elif isinstance(default, Body):
                value, body_data = await self.inject_body_param(
                    param_name, param_type, request, body_data
                )
                kwargs[param_name] = value

            elif isinstance(default, Query):
                kwargs[param_name] = self.inject_query_param(
                    param_name, param_type, default, query_params
                )

            elif isinstance(default, FieldInfo):
                key = default.alias or param_name
                if key in query_params:
                    kwargs[param_name] = coerce_query_param(
                        query_params[key], param_name, param_type, default
                    )
                elif default.has_default:
                    kwargs[param_name] = default.get_default()

            elif param_name in path_params:
                kwargs[param_name] = coerce_path_param(
                    path_params[param_name], param_name, param_type
                )

            elif param_name in query_params:
                kwargs[param_name] = self.inject_convention_query(
                    param_name, param_type, query_params[param_name]
                )

            elif param.default is not inspect.Parameter.empty:
                kwargs[param_name] = param.default

            else:
                # Required parameter with no source - raise validation error
                handler_name = getattr(handler, "__name__", repr(handler))
                _raise_validation_error(
                    "parameter",
                    param_name,
                    f"Required parameter '{param_name}' "
                    f"(type: {param_type.__name__ if hasattr(param_type, '__name__') else str(param_type)}) "
                    f"not provided for handler '{handler_name}'",
                    "value_error.missing",
                )

        return kwargs
