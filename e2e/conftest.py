import pytest

from pykour.testing import get_connection, release_connection, load_from_dir

from .main import app


@pytest.fixture(scope="session", autouse=True)
def setup_session():
    conn = get_connection(app)
    load_from_dir(conn, "./e2e/init_db/session")

    yield

    release_connection(app, conn)


@pytest.fixture(scope="function", autouse=True)
def setup_function():
    conn = get_connection(app)
    load_from_dir(conn, "./e2e/init_db/function")

    yield

    release_connection(app, conn)
