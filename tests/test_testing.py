import pytest

from pykour.exceptions import ResourceNotFoundException
from pykour.testing import perform, get, post, put, patch, delete, head, trace

from pykour import Pykour, Router
from pykour.middleware import UUIDMiddleware

app = Pykour()
app.add_middleware(UUIDMiddleware, header_name="X-TRACE-ID")

user_v1_router = Router()


@user_v1_router.get("/")
async def get_users():
    return {"users": []}


@user_v1_router.get("/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}


@user_v1_router.post("/")
async def create_user():
    return {"message": "User created"}


@user_v1_router.put("/{user_id}")
async def replace_user(user_id: int):
    return {"message": f"User {user_id} replaced"}


@user_v1_router.patch("/{user_id}")
async def update_user(user_id: int):
    return {"message": f"User {user_id} updated"}


@user_v1_router.delete("/{user_id}")
async def delete_user(user_id: int):
    return


api_v1_router = Router()
api_v1_router.add_router(user_v1_router, prefix="/users")


app.add_router(api_v1_router, prefix="/api/v1")


@app.get("/exception")
async def exception():
    raise ValueError()


@app.get("/http_exception")
async def http_exception():
    raise ResourceNotFoundException("Resource Not Found")


@pytest.mark.asyncio
async def test_get_method_without_path_variables():
    response = await perform(app, get("/api/v1/users"))
    response.is_ok().expect({"users": []})


@pytest.mark.asyncio
async def test_get_with_method_path_variables():
    response = await perform(app, get("/api/v1/users/1"))
    response.is_ok().expect({"user_id": 1})


@pytest.mark.asyncio
async def test_post_method():
    response = await perform(app, post("/api/v1/users", body='{"name": "John Doe"}'))
    response.is_created().expect({"message": "User created"})


@pytest.mark.asyncio
async def test_put_method():
    response = await perform(app, put("/api/v1/users/1", body='{"name": "John Doe"}'))
    response.is_ok().expect({"message": "User 1 replaced"})


@pytest.mark.asyncio
async def test_patch_method():
    response = await perform(app, patch("/api/v1/users/1", body='{"name": "John Doe"}'))
    response.is_ok().expect({"message": "User 1 updated"})


@pytest.mark.asyncio
async def test_delete_method():
    response = await perform(app, delete("/api/v1/users/1"))
    response.is_no_content().empty()


@pytest.mark.asyncio
async def test_not_supported_scheme():
    response = await perform(app, get("/api/v1/users", scheme="https"))
    response.is_bad_request().expect("Bad Request")


@pytest.mark.asyncio
async def test_not_supported_method():
    response = await perform(app, trace("/api/v1/users"))
    response.is_not_found().expect("Not Found")


@pytest.mark.asyncio
async def test_method_not_allowed():
    response = await perform(app, head("/api/v1/users"))
    response.is_method_not_allowed().expect("Method Not Allowed")


@pytest.mark.asyncio
async def test_route_not_found():
    response = await perform(app, get("/api/v2/users/1"))
    response.is_not_found().expect("Not Found")


@pytest.mark.asyncio
async def test_exception():
    response = await perform(app, get("/exception"))
    response.is_internal_server_error().expect("Internal Server Error")


@pytest.mark.asyncio
async def test_http_exception():
    response = await perform(app, get("/http_exception"))
    response.is_not_found().expect("Resource Not Found")
