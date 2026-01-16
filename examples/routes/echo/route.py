"""Route handlers for /echo."""

from pykour import JSONResponse, Request


async def post(request: Request) -> JSONResponse:
    """Echo request details."""
    body = await request.body()
    return JSONResponse(
        {
            "method": request.method,
            "path": request.path,
            "headers": request.headers,
            "body": body.decode("utf-8") if body else None,
        }
    )
