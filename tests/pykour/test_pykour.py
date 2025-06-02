import pytest

from pykour.pykour import Pykour


def test_pykour_init():
    app = Pykour()
    assert isinstance(app, Pykour)
