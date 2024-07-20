import os

import pytest
from pykour.db.session import Session


TEST_DB = "test.db"


@pytest.fixture
def sqlite_session():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    session = Session(db_type="sqlite", url=TEST_DB)
    yield session
    session.close()
    os.remove(TEST_DB)


def test_execute(sqlite_session):
    sqlite_session.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    sqlite_session.commit()

    sqlite_session.execute("INSERT INTO test (name) VALUES (?)", ("Alice",))
    sqlite_session.commit()

    sqlite_session.execute("SELECT * FROM test")
    result = sqlite_session.fetchall()
    assert len(result) == 1
    assert result[0][1] == "Alice"


def test_fetchone(sqlite_session):
    sqlite_session.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    sqlite_session.commit()

    sqlite_session.execute("INSERT INTO test (name) VALUES (?)", ("Bob",))
    sqlite_session.commit()

    sqlite_session.execute("SELECT * FROM test WHERE name = ?", ("Bob",))
    result = sqlite_session.fetchone()
    assert result[1] == "Bob"


def test_commit_and_rollback(sqlite_session):
    sqlite_session.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    sqlite_session.commit()

    sqlite_session.execute("INSERT INTO test (name) VALUES (?)", ("Charlie",))
    sqlite_session.rollback()

    sqlite_session.execute("SELECT * FROM test WHERE name = ?", ("Charlie",))
    result = sqlite_session.fetchall()
    assert len(result) == 0


def test_close(sqlite_session):
    sqlite_session.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    sqlite_session.commit()
    sqlite_session.close()

    with pytest.raises(AttributeError):
        sqlite_session.execute("SELECT * FROM test")


def test_unsupported_session_type():
    with pytest.raises(ValueError):
        Session(db_type="notfound", url="notfound://localhost:3306/test")


def test_from_config():
    class MockConfig:
        def get_datasource_type(self):
            return "sqlite"

        def get_datasource_url(self):
            return TEST_DB

        def get_datasource_username(self):
            return None

        def get_datasource_password(self):
            return None

    mock_config = MockConfig()
    session = Session.from_config(mock_config)
    assert session.db_type == "sqlite"
    assert session.conn is not None
    session.close()
    os.remove(TEST_DB)
