import pytest

from pykour.pykour import Pykour


@pytest.mark.it("should initialize the Pykour app")
def test_init():

    app = Pykour()
    assert app is not None
    assert app.app is not None
    assert app.config is not None


@pytest.mark.it("should initialize the Pykour app with a prefix")
def test_init_with_prefix():
    app = Pykour(prefix="/api")
    assert app._prefix == "/api"
