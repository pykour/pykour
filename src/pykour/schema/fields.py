"""Field descriptors for schema definition."""

from typing import Any, Callable

from pykour.schema.validators import (
    Constraint,
    Ge,
    Gt,
    Le,
    Lt,
    MaxLength,
    MinLength,
    Pattern,
)

# Sentinel for missing default
MISSING = object()


class FieldInfo:
    """Metadata for schema fields."""

    def __init__(
        self,
        default: Any = MISSING,
        *,
        default_factory: Callable[[], Any] | None = None,
        alias: str | None = None,
        ge: int | float | None = None,
        le: int | float | None = None,
        gt: int | float | None = None,
        lt: int | float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        description: str | None = None,
    ) -> None:
        if default is not MISSING and default_factory is not None:
            raise ValueError(
                "Cannot specify both 'default' and 'default_factory'; "
                "get_default() would ignore 'default' when 'default_factory' is set"
            )
        self.default = default
        self.default_factory = default_factory
        self.alias = alias
        self.ge = ge
        self.le = le
        self.gt = gt
        self.lt = lt
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.description = description

    @property
    def has_default(self) -> bool:
        """Check if field has a default value."""
        return self.default is not MISSING or self.default_factory is not None

    def get_default(self) -> Any:
        """Get the default value."""
        if self.default_factory is not None:
            return self.default_factory()
        return self.default

    def get_constraints(self) -> list[Constraint]:
        """Build constraint list from field info."""
        constraints: list[Constraint] = []
        if self.ge is not None:
            constraints.append(Ge(self.ge))
        if self.gt is not None:
            constraints.append(Gt(self.gt))
        if self.le is not None:
            constraints.append(Le(self.le))
        if self.lt is not None:
            constraints.append(Lt(self.lt))
        if self.min_length is not None:
            constraints.append(MinLength(self.min_length))
        if self.max_length is not None:
            constraints.append(MaxLength(self.max_length))
        if self.pattern is not None:
            constraints.append(Pattern(self.pattern))
        return constraints


def Field(
    default: Any = MISSING,
    *,
    default_factory: Callable[[], Any] | None = None,
    alias: str | None = None,
    ge: int | float | None = None,
    le: int | float | None = None,
    gt: int | float | None = None,
    lt: int | float | None = None,
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
    description: str | None = None,
) -> Any:
    """Create a field with metadata."""
    return FieldInfo(
        default=default,
        default_factory=default_factory,
        alias=alias,
        ge=ge,
        le=le,
        gt=gt,
        lt=lt,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
        description=description,
    )


class Path(FieldInfo):
    """Marker for path parameters extracted from URL segments.

    Use this to annotate handler parameters that should be extracted
    from dynamic URL path segments like /users/[id].

    Example:
        # routes/users/[id]/route.py
        async def get(request: Request, id: int = Path()) -> JSONResponse:
            return JSONResponse({"user_id": id})

        # With validation
        async def get(request: Request, id: int = Path(ge=1)) -> JSONResponse:
            return JSONResponse({"user_id": id})
    """

    ...


class Query(FieldInfo):
    """Marker for query parameters extracted from URL query string.

    Use this to annotate handler parameters that should be extracted
    from the URL query string (?key=value).

    Example:
        async def get(
            request: Request,
            page: int = Query(default=1, ge=1),
            limit: int = Query(default=10, le=100),
        ) -> JSONResponse:
            return JSONResponse({"page": page, "limit": limit})

        # With alias for different query param name
        async def get(
            request: Request,
            page_num: int = Query(default=1, alias="page"),
        ) -> JSONResponse:
            return JSONResponse({"page": page_num})
    """

    ...


class Body(FieldInfo):
    """Marker for request body parsed from JSON.

    Use this to annotate handler parameters that should be parsed
    from the request body. Can be combined with Schema classes
    for automatic validation.

    Example:
        # With Schema for validation
        class CreateUserSchema(Schema):
            name: str
            email: str

        async def post(
            request: Request,
            data: CreateUserSchema = Body(),
        ) -> JSONResponse:
            return JSONResponse({"name": data.name})

        # Raw dict access
        async def post(
            request: Request,
            data: dict = Body(),
        ) -> JSONResponse:
            return JSONResponse(data)
    """

    ...
