import pytest

from pykour.testing import perform, get, post, put, delete, json_to_string


@pytest.mark.asyncio
async def test_index():
    from .main import app

    result = await perform(app, get("/api/v1/user"))
    result.is_ok().expect([{"username": "alice", "email": "alice@example.com"}])


@pytest.mark.asyncio
async def test_get():
    from .main import app

    result = await perform(app, get("/api/v1/user/1"))
    result.is_ok().expect({"username": "alice", "email": "alice@example.com"})


@pytest.mark.asyncio
async def test_create():
    from .main import app

    result = await perform(app, post("/api/v1/user", json_to_string({"username": "bob", "email": "bob@example.com"})))
    result.is_created().expect({"status": "ok"})

    result = await perform(app, get("/api/v1/user"))
    result.is_ok().expect(
        [
            {"username": "alice", "email": "alice@example.com"},
            {"username": "bob", "email": "bob@example.com"},
        ]
    )


@pytest.mark.asyncio
async def test_update():
    from .main import app

    result = await perform(
        app, put("/api/v1/user/1", json_to_string({"username": "alice1", "email": "alice1@example.com"}))
    )
    result.is_ok().expect({"status": "ok"})

    result = await perform(app, get("/api/v1/user"))
    result.is_ok().expect([{"username": "alice1", "email": "alice1@example.com"}])


@pytest.mark.asyncio
async def test_delete():
    from .main import app

    result = await perform(app, delete("/api/v1/user/1"))
    result.is_no_content()

    result = await perform(app, get("/api/v1/user"))
    result.is_ok().expect([])
