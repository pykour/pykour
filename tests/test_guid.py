import time

import pytest

from pykour.guid import GUID


@pytest.mark.it("should generate a random GUID")
def test_generate():
    assert GUID.generate() != GUID.generate()


@pytest.mark.it("should generate a GUID of the correct length")
def test_length():
    assert len(GUID.generate()) == 24


@pytest.mark.it("should generate a GUID with the correct characters")
def test_characters():
    guid = GUID.generate()
    for c in guid:
        assert c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


@pytest.mark.it("should generate a GUID so fast")
def test_speed():
    start_time = time.time()
    for _ in range(10_000):
        GUID.generate()
    end_time = time.time()

    assert end_time - start_time < 1
