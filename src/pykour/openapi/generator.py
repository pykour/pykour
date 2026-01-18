"""OpenAPI schema generator."""

import inspect
import re
from typing import Any, Callable, get_origin, get_type_hints

from pykour.openapi.config import OpenAPIConfig
from pykour.openapi.schema_converter import SchemaConverter
from pykour.response import (
    EventSourceResponse,
    FileResponse,
    HTMLResponse,
    PlainTextResponse,
    Response,
    StreamingResponse,
)
from pykour.router import Route, Router
from pykour.schema.fields import Body, FieldInfo, Path, Query
from pykour.schema.form_fields import File, Form


class OpenAPIGenerator:
    """Generate OpenAPI schema from Pykour router."""

    def __init__(self, router: Router, config: OpenAPIConfig) -> None:
        """Initialize generator.

        Args:
            router: Pykour router instance.
            config: OpenAPI configuration.
        """
        self._router = router
        self._config = config
        self._schema_converter = SchemaConverter()
        self._collected_tags: set[str] = set()

    def generate(self) -> dict[str, Any]:
        """Generate complete OpenAPI document.

        Returns:
            OpenAPI document dictionary.
        """
        paths = self._generate_paths()
        components = self._generate_components()
        tags = self._generate_tags()

        doc: dict[str, Any] = {
            "openapi": self._config.openapi_version,
            "info": self._generate_info(),
            "paths": paths,
        }

        if components:
            doc["components"] = components

        if tags:
            doc["tags"] = tags

        if self._config.servers:
            doc["servers"] = [
                {
                    "url": server.url,
                    **(
                        {"description": server.description}
                        if server.description
                        else {}
                    ),
                }
                for server in self._config.servers
            ]

        return doc

    def _generate_info(self) -> dict[str, Any]:
        """Generate info object."""
        info: dict[str, Any] = {
            "title": self._config.title,
            "version": self._config.version,
        }

        if self._config.description:
            info["description"] = self._config.description

        if self._config.summary:
            info["summary"] = self._config.summary

        if self._config.terms_of_service:
            info["termsOfService"] = self._config.terms_of_service

        if self._config.contact:
            contact_obj: dict[str, str] = {}
            if self._config.contact.name:
                contact_obj["name"] = self._config.contact.name
            if self._config.contact.url:
                contact_obj["url"] = self._config.contact.url
            if self._config.contact.email:
                contact_obj["email"] = self._config.contact.email
            if contact_obj:
                info["contact"] = contact_obj

        if self._config.license:
            license_obj: dict[str, str] = {"name": self._config.license.name}
            if self._config.license.url:
                license_obj["url"] = self._config.license.url
            if self._config.license.identifier:
                license_obj["identifier"] = self._config.license.identifier
            info["license"] = license_obj

        return info

    def _generate_paths(self) -> dict[str, dict[str, Any]]:
        """Generate paths object from router routes."""
        paths: dict[str, dict[str, Any]] = {}

        for route in self._router.routes:
            openapi_path = self._convert_path_pattern(route.path_pattern)

            # Skip documentation endpoints
            if openapi_path in (
                self._config.docs_url,
                self._config.openapi_url,
                self._config.redoc_url,
            ):
                continue

            path_item = self._generate_path_item(route)
            if path_item:
                paths[openapi_path] = path_item

        return paths

    def _generate_path_item(self, route: Route) -> dict[str, Any]:
        """Generate path item from route."""
        path_item: dict[str, Any] = {}

        for method, handler in route.handlers.items():
            # Skip WebSocket
            if method == "WEBSOCKET":
                continue

            # Skip HEAD/OPTIONS unless configured
            if method == "HEAD" and not self._config.include_head_operations:
                continue
            if method == "OPTIONS" and not self._config.include_options_operations:
                continue

            operation = self._generate_operation(
                method, handler, route.path_pattern, route.param_names
            )

            # Map method to path item key
            method_key = method.lower()
            if method_key in (
                "get",
                "put",
                "post",
                "delete",
                "options",
                "head",
                "patch",
                "trace",
            ):
                path_item[method_key] = operation

        return path_item

    def _generate_operation(
        self,
        method: str,
        handler: Callable[..., Any],
        path_pattern: str,
        path_param_names: list[str],
    ) -> dict[str, Any]:
        """Generate operation object from handler."""
        operation: dict[str, Any] = {}

        # Extract docstring for summary and description
        docstring = inspect.getdoc(handler)
        if docstring:
            lines = docstring.strip().split("\n")
            operation["summary"] = lines[0]
            if len(lines) > 1:
                # Join remaining lines as description
                desc = "\n".join(lines[1:]).strip()
                if desc:
                    operation["description"] = desc

        # Generate operation ID
        operation["operationId"] = self._generate_operation_id(
            method, path_pattern, handler
        )

        # Extract tag from path
        tag = self._extract_tag(path_pattern)
        if tag:
            operation["tags"] = [tag]
            self._collected_tags.add(tag)

        # Extract parameters and request body from handler signature
        parameters, request_body = self._extract_parameters(handler, path_param_names)

        if parameters:
            operation["parameters"] = parameters

        if request_body:
            operation["requestBody"] = request_body

        # Generate responses
        operation["responses"] = self._generate_responses(handler)

        return operation

    def _extract_parameters(
        self, handler: Callable[..., Any], path_param_names: list[str]
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        """Extract parameters from handler signature.

        Returns:
            Tuple of (parameters list, request body object or None).
        """
        parameters: list[dict[str, Any]] = []
        request_body: dict[str, Any] | None = None

        # Track form/file fields for multipart request body
        form_properties: dict[str, Any] = {}
        form_required: list[str] = []
        has_file_or_form = False

        try:
            sig = inspect.signature(handler)
            hints = get_type_hints(handler)
        except Exception:
            return parameters, request_body

        for param_name, param in sig.parameters.items():
            # Skip 'self', 'cls', 'request'
            if param_name in ("self", "cls", "request"):
                continue

            param_type = hints.get(param_name, str)
            default = param.default

            # Determine parameter location and info
            if isinstance(default, Path):
                # Path parameter
                param_obj = self._create_parameter(
                    name=param_name,
                    location="path",
                    param_type=param_type,
                    field_info=default,
                    required=True,
                )
                parameters.append(param_obj)

            elif isinstance(default, Query):
                # Query parameter
                param_obj = self._create_parameter(
                    name=default.alias or param_name,
                    location="query",
                    param_type=param_type,
                    field_info=default,
                    required=not default.has_default,
                )
                parameters.append(param_obj)

            elif isinstance(default, Body):
                # Request body
                request_body = self._create_request_body(param_type, default)

            elif isinstance(default, File):
                # File upload field
                has_file_or_form = True
                field_name = default.alias or param_name
                schema = self._create_file_schema(param_type, default)
                form_properties[field_name] = schema
                if not default.has_default:
                    form_required.append(field_name)

            elif isinstance(default, Form):
                # Form text field
                has_file_or_form = True
                field_name = default.alias or param_name
                schema = self._schema_converter._convert_type(param_type, default)
                form_properties[field_name] = schema
                if not default.has_default:
                    form_required.append(field_name)

            elif isinstance(default, FieldInfo):
                # Generic FieldInfo - treat as query parameter
                param_obj = self._create_parameter(
                    name=default.alias or param_name,
                    location="query",
                    param_type=param_type,
                    field_info=default,
                    required=not default.has_default,
                )
                parameters.append(param_obj)

            elif param_name in path_param_names:
                # Convention-based path parameter
                param_obj = self._create_parameter(
                    name=param_name,
                    location="path",
                    param_type=param_type,
                    field_info=None,
                    required=True,
                )
                parameters.append(param_obj)

        # Create multipart request body if we have file or form fields
        if has_file_or_form:
            request_body = self._create_multipart_request_body(
                form_properties, form_required
            )

        return parameters, request_body

    def _create_parameter(
        self,
        name: str,
        location: str,
        param_type: type,
        field_info: FieldInfo | None,
        required: bool,
    ) -> dict[str, Any]:
        """Create a parameter object."""
        schema = self._schema_converter._convert_type(param_type, field_info)

        if field_info:
            schema = self._schema_converter._apply_constraints(schema, field_info)

        param: dict[str, Any] = {
            "name": name,
            "in": location,
            "schema": schema,
        }

        if required:
            param["required"] = True

        if field_info and field_info.description:
            param["description"] = field_info.description

        return param

    def _create_request_body(
        self, param_type: type, field_info: Body
    ) -> dict[str, Any]:
        """Create a request body object."""
        # Import here to avoid circular import
        from pykour.schema.base import Schema

        content_schema: dict[str, Any]

        if isinstance(param_type, type) and issubclass(param_type, Schema):
            # Schema type - create reference
            schema_name = param_type.__name__
            # Convert schema and store in definitions
            self._schema_converter.convert(param_type)
            content_schema = {"$ref": f"#/components/schemas/{schema_name}"}
        else:
            # Other types
            content_schema = self._schema_converter._convert_type(
                param_type, field_info
            )

        media_type: dict[str, Any] = {"schema": content_schema}

        body: dict[str, Any] = {
            "content": {"application/json": media_type},
            "required": not field_info.has_default,
        }

        if field_info.description:
            body["description"] = field_info.description

        return body

    def _create_file_schema(self, param_type: type, field_info: File) -> dict[str, Any]:
        """Create OpenAPI schema for file upload field.

        Args:
            param_type: Type annotation for the parameter.
            field_info: File marker instance.

        Returns:
            Schema object for the file field.
        """
        schema: dict[str, Any]

        # Check if it's a list[UploadFile]
        origin = get_origin(param_type)
        if origin is list:
            schema = {
                "type": "array",
                "items": {"type": "string", "format": "binary"},
            }
        else:
            schema = {"type": "string", "format": "binary"}

        if field_info.description:
            schema["description"] = field_info.description

        return schema

    def _create_multipart_request_body(
        self,
        properties: dict[str, Any],
        required: list[str],
    ) -> dict[str, Any]:
        """Create request body for multipart/form-data.

        Args:
            properties: Schema properties for form fields and files.
            required: List of required field names.

        Returns:
            Request body object for multipart/form-data.
        """
        content_schema: dict[str, Any] = {
            "type": "object",
            "properties": properties,
        }

        if required:
            content_schema["required"] = required

        return {
            "content": {"multipart/form-data": {"schema": content_schema}},
            "required": bool(required),
        }

    def _generate_responses(
        self, handler: Callable[..., Any]
    ) -> dict[str, dict[str, Any]]:
        """Generate responses from handler return type and @status_code decorators."""
        from pykour.status_code import get_status_code_info

        responses: dict[str, dict[str, Any]] = {}

        # Try to get return type hint
        try:
            hints = get_type_hints(handler)
            return_type = hints.get("return", Response)
        except Exception:
            return_type = Response

        # Get declared status codes from @status_code decorator
        status_infos = get_status_code_info(handler)

        # Determine content schema based on return type
        content_schema = self._get_response_content(return_type)

        if status_infos:
            # Use declared status codes
            for info in status_infos:
                response_obj: dict[str, Any] = {
                    "description": info.description
                    or self._get_default_description(info.code)
                }
                # Only add content for success responses (2xx)
                if 200 <= info.code < 300 and content_schema:
                    response_obj["content"] = content_schema
                responses[str(info.code)] = response_obj
        else:
            # Fall back to default 200 response
            if content_schema:
                responses["200"] = {
                    "description": "Successful response",
                    "content": content_schema,
                }
            else:
                responses["200"] = {"description": "Successful response"}

        # Add common error responses (if not already declared)
        if "422" not in responses:
            responses["422"] = {
                "description": "Validation Error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/ValidationError"}
                    }
                },
            }

        return responses

    def _get_response_content(self, return_type: type) -> dict[str, Any] | None:
        """Get content schema for a return type."""
        from pykour.response import JSONResponse

        if return_type is JSONResponse or return_type is dict:
            return {"application/json": {"schema": {"type": "object"}}}
        elif return_type is HTMLResponse:
            return {"text/html": {"schema": {"type": "string"}}}
        elif return_type is PlainTextResponse:
            return {"text/plain": {"schema": {"type": "string"}}}
        elif return_type is FileResponse:
            return {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            }
        elif return_type is StreamingResponse:
            return {
                "application/octet-stream": {
                    "schema": {"type": "string", "format": "binary"}
                }
            }
        elif return_type is EventSourceResponse:
            return {"text/event-stream": {"schema": {"type": "string"}}}
        return None

    def _get_default_description(self, code: int) -> str:
        """Get default description for HTTP status code."""
        descriptions = {
            200: "Successful response",
            201: "Created",
            202: "Accepted",
            204: "No Content",
            400: "Bad Request",
            401: "Unauthorized",
            403: "Forbidden",
            404: "Not Found",
            405: "Method Not Allowed",
            409: "Conflict",
            422: "Validation Error",
            500: "Internal Server Error",
        }
        return descriptions.get(code, f"Response {code}")

    def _generate_components(self) -> dict[str, Any]:
        """Generate components object."""
        components: dict[str, Any] = {}

        # Get schema definitions from converter
        schemas = self._schema_converter.get_definitions()

        # Add ValidationError schema
        schemas["ValidationError"] = {
            "type": "object",
            "properties": {
                "error": {"type": "string"},
                "detail": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/ErrorDetail"},
                },
            },
        }

        schemas["ErrorDetail"] = {
            "type": "object",
            "properties": {
                "loc": {"type": "array", "items": {"type": "string"}},
                "msg": {"type": "string"},
                "type": {"type": "string"},
            },
        }

        if schemas:
            components["schemas"] = schemas

        return components

    def _generate_tags(self) -> list[dict[str, Any]]:
        """Generate tags from collected routes."""
        tags: list[dict[str, Any]] = []

        # Use configured tags if available
        if self._config.tags:
            for tag_config in self._config.tags:
                tag: dict[str, Any] = {"name": tag_config.get("name", "")}
                if "description" in tag_config:
                    tag["description"] = tag_config["description"]
                tags.append(tag)
        else:
            # Generate tags from collected paths
            for tag_name in sorted(self._collected_tags):
                tags.append({"name": tag_name})

        return tags

    def _convert_path_pattern(self, pykour_pattern: str) -> str:
        """Convert Pykour path pattern to OpenAPI format.

        Examples:
            /api/users/[id] -> /api/users/{id}
            /docs/[...slug] -> /docs/{slug}
        """
        # Dynamic segment: [id] -> {id}
        result = re.sub(r"\[([^\]\.]+)\]", r"{\1}", pykour_pattern)
        # Catch-all: [...slug] -> {slug}
        result = re.sub(r"\[\.\.\.([^\]]+)\]", r"{\1}", result)
        return result

    def _extract_tag(self, path_pattern: str) -> str | None:
        """Extract tag from path pattern.

        Uses the first meaningful path segment after removing common prefixes.
        """
        segments = [s for s in path_pattern.split("/") if s]

        if not segments:
            return None

        # Skip common prefixes like 'api', 'v1', 'v2', etc.
        common_prefixes = {"api", "v1", "v2", "v3"}

        for segment in segments:
            # Skip dynamic/catch-all segments
            if segment.startswith("["):
                continue
            # Skip common prefixes
            if segment.lower() in common_prefixes:
                continue
            return segment

        # Fallback to first non-dynamic segment
        for segment in segments:
            if not segment.startswith("["):
                return segment

        return None

    def _generate_operation_id(
        self, method: str, path_pattern: str, handler: Callable[..., Any]
    ) -> str:
        """Generate unique operation ID."""
        # Use handler name if available
        handler_name = getattr(handler, "__name__", "")
        if handler_name and handler_name not in (
            "get",
            "post",
            "put",
            "delete",
            "patch",
        ):
            return handler_name

        # Generate from path
        path_parts = [s for s in path_pattern.split("/") if s]
        clean_parts = []
        for part in path_parts:
            if part.startswith("[...") and part.endswith("]"):
                clean_parts.append(part[4:-1])
            elif part.startswith("[") and part.endswith("]"):
                clean_parts.append(f"by_{part[1:-1]}")
            else:
                clean_parts.append(part)

        if clean_parts:
            return f"{method.lower()}_{'_'.join(clean_parts)}"
        return f"{method.lower()}_root"
