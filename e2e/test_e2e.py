import pytest

from pykour.testing import perform, get, post


@pytest.mark.asyncio
async def test_index():
    from .main import app

    result = await perform(app, get("/"))
    result.is_ok().expect([{"username": "alice", "email": "alice@example.com"}])
