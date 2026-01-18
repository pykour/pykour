"""HTTP request handler for Pykour application."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, cast

from pykour.cache.decorators import get_cache_evict_info, get_cache_info
from pykour.conditional import get_etag_info, get_last_modified_info
from pykour.core.handler import (
    check_etag_match,
    compute_etag,
    deserialize_response,
    extract_last_modified,
    format_last_modified,
    interpolate_cache_key,
    interpolate_header_value,
    parse_if_modified_since,
    serialize_response,
)
from pykour.header import get_header_info
from pykour.request import Request
from pykour.response import JSONResponse, Response
from pykour.status_code import get_default_status_code, get_method_default_status_code

if TYPE_CHECKING:
    from pykour.cache.storage import CacheStorage
    from pykour.injection import ParameterInjector
    from pykour.router import Router
    from pykour.types import Receive, Scope


class RequestHandler:
    """Handles HTTP request routing and response processing.

    This class encapsulates the core request handling logic, including:
    - Route matching
    - Parameter injection
    - Cache lookup and storage
    - ETag and Last-Modified handling
    - Status code and header processing
    """

    def __init__(
        self,
        router: "Router",
        injector: "ParameterInjector",
        cache: "CacheStorage | None",
    ) -> None:
        """Initialize request handler.

        Args:
            router: Router instance for route matching.
            injector: Parameter injector for handler parameter resolution.
            cache: Optional cache storage for response caching.
        """
        self._router = router
        self._injector = injector
        self._cache = cache

    async def handle(self, scope: "Scope", receive: "Receive") -> Response:
        """Process HTTP request and return response.

        Args:
            scope: ASGI HTTP scope.
            receive: ASGI receive callable.

        Returns:
            Response object to be sent to the client.
        """
        path = scope.get("path", "/")
        method = scope.get("method", "GET")

        handler, path_params = self._router.match(path, method)

        # Automatic HEAD support: use GET handler if HEAD is not explicitly defined
        is_auto_head = False
        if handler is None and method == "HEAD":
            handler, path_params = self._router.match(path, "GET")
            is_auto_head = handler is not None

        if handler is not None:
            request = Request(scope, receive, path_params)
            return await self._execute_handler(
                handler, request, path_params, is_auto_head
            )

        # Check if path exists but method is not allowed
        allowed_methods = self._router.get_allowed_methods(path)
        if allowed_methods:
            # RFC 7231: Allow header should list permitted methods
            allow_header = ", ".join(sorted(m.upper() for m in allowed_methods))
            return JSONResponse(
                content={"error": "Method Not Allowed"},
                status_code=405,
                headers={"Allow": allow_header},
            )

        # Not found
        return JSONResponse(
            content={"error": "Not Found"},
            status_code=404,
        )

    async def _execute_handler(
        self,
        handler: Any,
        request: Request,
        path_params: dict[str, Any],
        is_auto_head: bool,
    ) -> Response:
        """Execute route handler with all decorators applied.

        Args:
            handler: Route handler function.
            request: Request object.
            path_params: Path parameters extracted from URL.
            is_auto_head: Whether this is an automatic HEAD response.

        Returns:
            Response from handler or from cache.
        """
        kwargs = await self._injector.inject(handler, request, path_params)

        # Check for @cache decorator and try to serve from cache
        cache_infos = get_cache_info(handler)
        etag_infos = get_etag_info(handler)
        last_modified_infos = get_last_modified_info(handler)
        cache_key: str | None = None

        # Try to serve from cache
        cached_response = await self._check_cache(
            handler, request, kwargs, cache_infos, etag_infos
        )
        if cached_response is not None:
            return cached_response

        # Execute handler
        result = handler(**kwargs)
        if inspect.isawaitable(result):
            response = cast(Response, await result)
        else:
            response = cast(Response, result)

        # Apply declarative status code
        response = self._apply_status_code(handler, request, response)

        # Apply declarative headers from @header decorator
        response = self._apply_headers(handler, kwargs, response)

        # Handle @etag decorator
        computed_etag = self._apply_etag(etag_infos, request, response)
        if isinstance(computed_etag, Response):
            return computed_etag  # 304 Not Modified

        # Handle @last_modified decorator
        lm_response = self._apply_last_modified(
            last_modified_infos, request, response, computed_etag
        )
        if lm_response is not None:
            return lm_response  # 304 Not Modified

        # Cache response if @cache decorator is present
        if cache_infos and self._cache is not None:
            cache_info = cache_infos[0]
            cache_key = interpolate_cache_key(cache_info.key, kwargs)
            # Only cache successful responses (2xx)
            if 200 <= response.status_code < 300:
                serialized = serialize_response(response)
                await self._cache.set(cache_key, serialized, cache_info.ttl)

        # Handle @cache_evict decorator
        await self._handle_cache_evict(handler, kwargs)

        # For automatic HEAD, return headers only (empty body)
        if is_auto_head:
            return Response(
                content=b"",
                status_code=response.status_code,
                headers=response.headers,
                media_type=response.media_type,
            )

        return response

    async def _check_cache(
        self,
        handler: Any,
        request: Request,
        kwargs: dict[str, Any],
        cache_infos: list[Any],
        etag_infos: list[Any],
    ) -> Response | None:
        """Check cache for existing response.

        Args:
            handler: Route handler function.
            request: Request object.
            kwargs: Handler keyword arguments.
            cache_infos: Cache decorator info list.
            etag_infos: ETag decorator info list.

        Returns:
            Cached response or None if not found.
        """
        if not cache_infos or self._cache is None:
            return None

        cache_info = cache_infos[0]  # Use first cache decorator
        cache_key = interpolate_cache_key(cache_info.key, kwargs)
        cached_data = await self._cache.get(cache_key)

        if cached_data is None:
            return None

        cached_response = deserialize_response(cached_data)

        # Check ETag on cache hit (returns 304 without handler execution)
        if etag_infos:
            etag_info = etag_infos[0]
            computed_etag = compute_etag(
                cached_response.body,
                weak=etag_info.weak,
                algorithm=etag_info.algorithm,
            )
            if_none_match = request.headers.get("if-none-match")
            if if_none_match and check_etag_match(if_none_match, computed_etag):
                # Return 304 Not Modified (no body)
                return Response(
                    content=b"",
                    status_code=304,
                    headers={"ETag": computed_etag},
                )
            # Add ETag to cached response
            cached_response.set_header("ETag", computed_etag)

        return cached_response

    def _apply_status_code(
        self, handler: Any, request: Request, response: Response
    ) -> Response:
        """Apply declarative status code from decorators.

        Args:
            handler: Route handler function.
            request: Request object.
            response: Response to modify.

        Returns:
            Response with applied status code.
        """
        declared_status = get_default_status_code(handler)
        if declared_status is not None and response.status_code == 200:
            response.status_code = declared_status
        elif response.status_code == 200:
            # Apply method-based default when no decorator
            method = request.method
            response.status_code = get_method_default_status_code(method)
        return response

    def _apply_headers(
        self, handler: Any, kwargs: dict[str, Any], response: Response
    ) -> Response:
        """Apply declarative headers from @header decorator.

        Args:
            handler: Route handler function.
            kwargs: Handler keyword arguments.
            response: Response to modify.

        Returns:
            Response with applied headers.
        """
        header_infos = get_header_info(handler)
        for header_info in header_infos:
            # Check condition (e.g., on_status)
            if header_info.condition is not None and not header_info.condition(
                response.status_code
            ):
                continue

            # Interpolate header value
            header_value = interpolate_header_value(
                header_info.value_template, kwargs, response
            )
            if header_value is not None:
                response.add_header(header_info.name, header_value)

        return response

    def _apply_etag(
        self,
        etag_infos: list[Any],
        request: Request,
        response: Response,
    ) -> str | Response | None:
        """Apply ETag decorator and handle If-None-Match.

        Args:
            etag_infos: ETag decorator info list.
            request: Request object.
            response: Response to modify.

        Returns:
            Computed ETag string, 304 Response if not modified, or None.
        """
        if not etag_infos:
            return None

        etag_info = etag_infos[0]
        computed_etag = compute_etag(
            response.body,
            weak=etag_info.weak,
            algorithm=etag_info.algorithm,
        )
        response.set_header("ETag", computed_etag)

        # Check If-None-Match header
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and check_etag_match(if_none_match, computed_etag):
            # Return 304 Not Modified (no body)
            return Response(
                content=b"",
                status_code=304,
                headers={"ETag": computed_etag},
            )

        return computed_etag

    def _apply_last_modified(
        self,
        last_modified_infos: list[Any],
        request: Request,
        response: Response,
        computed_etag: str | None,
    ) -> Response | None:
        """Apply Last-Modified decorator and handle If-Modified-Since.

        Args:
            last_modified_infos: Last-Modified decorator info list.
            request: Request object.
            response: Response to modify.
            computed_etag: Previously computed ETag value.

        Returns:
            304 Response if not modified, or None.
        """
        if not last_modified_infos:
            return None

        lm_info = last_modified_infos[0]
        last_mod_time = extract_last_modified(
            response,
            lm_info.static_value,
            lm_info.response_field,
            lm_info.format,
        )

        if not last_mod_time:
            return None

        lm_header = format_last_modified(last_mod_time)
        response.set_header("Last-Modified", lm_header)

        # Check If-Modified-Since header
        if_modified_since = request.headers.get("if-modified-since")
        if if_modified_since:
            ims_time = parse_if_modified_since(if_modified_since)
            if ims_time and last_mod_time <= ims_time:
                # Return 304 Not Modified (no body)
                headers_304: dict[str, str] = {"Last-Modified": lm_header}
                if computed_etag:
                    headers_304["ETag"] = computed_etag
                return Response(
                    content=b"",
                    status_code=304,
                    headers=headers_304,
                )

        return None

    async def _handle_cache_evict(self, handler: Any, kwargs: dict[str, Any]) -> None:
        """Handle @cache_evict decorator.

        Args:
            handler: Route handler function.
            kwargs: Handler keyword arguments.
        """
        if self._cache is None:
            return

        evict_infos = get_cache_evict_info(handler)
        for evict_info in evict_infos:
            evict_key = interpolate_cache_key(evict_info.key, kwargs)
            if evict_info.all_entries:
                await self._cache.delete_pattern(evict_key)
            else:
                await self._cache.delete(evict_key)
