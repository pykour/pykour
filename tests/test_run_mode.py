import os

import pytest

from pykour.run_mode import RunMode


@pytest.mark.it("should return False if PYKOUR_ENV is not set")
def test_is_production01():
    os.environ.pop("PYKOUR_ENV", None)
    assert RunMode.is_production() is False


@pytest.mark.it("should return True if PYKOUR_ENV is set to production")
def test_is_production02():
    os.environ["PYKOUR_ENV"] = "production"
    assert RunMode.is_production() is True


@pytest.mark.it("should return False if PYKOUR_ENV is set to development")
def test_is_production03():
    os.environ["PYKOUR_ENV"] = "development"
    assert RunMode.is_production() is False


@pytest.mark.it("should return True if PYKOUR_ENV is not set")
def test_is_development01():
    os.environ.pop("PYKOUR_ENV", None)
    assert RunMode.is_development() is True


@pytest.mark.it("should return False if PYKOUR_ENV is set to production")
def test_is_development02():
    os.environ["PYKOUR_ENV"] = "production"
    assert RunMode.is_development() is False


@pytest.mark.it("should return True if PYKOUR_ENV is set to development")
def test_is_development03():
    os.environ["PYKOUR_ENV"] = "development"
    assert RunMode.is_development() is True
