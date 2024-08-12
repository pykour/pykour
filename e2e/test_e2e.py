import pytest

from pykour.testing import perform, get


@pytest.mark.asyncio
async def test_hello():
    from .main import app

    result = await perform(app, get("/"))
    result.is_ok().expect({"message": "Hello, World!"})
