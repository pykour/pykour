"""Route handlers for testing body parameter validation."""

from pykour import Body, Field, JSONResponse, Request, Schema


class UserSchema(Schema):
    """Schema for user data."""

    name: str = Field(min_length=1)
    email: str = Field(pattern=r"^[^@]+@[^@]+\.[^@]+$")


async def post(
    request: Request,
    user: UserSchema = Body(),  # type: ignore[assignment]
) -> JSONResponse:
    """Handler with body schema validation."""
    return JSONResponse({"user": user.model_dump()})
