import pytest
from pykour.db.connection import Connection
from pykour.config import Config


@pytest.fixture
def mock_config():
    config = Config()
    config.config = {
        "pykour": {
            "datasource": {
                "type": "sqlite",
                "url": ":memory:",
                "username": "user",
                "password": "pass",
            }
        }
    }
    return config


@pytest.fixture
def mock_config_unsupported_type():
    config = Config()
    config.config = {
        "pykour": {
            "datasource": {
                "type": "unsupported_db",
                "url": ":memory:",
                "username": "user",
                "password": "pass",
            }
        }
    }
    return config


def test_connection_initialization_with_sqlite_succeeds(mock_config):
    connection = Connection.from_config(mock_config)
    assert connection.db_type == "sqlite"
    assert connection.conn is not None


def test_connection_initialization_with_unsupported_db_type_raises_error(mock_config_unsupported_type):
    with pytest.raises(ValueError):
        Connection.from_config(mock_config_unsupported_type)


def test_fetch_one_returns_correct_data(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    result = connection.fetch_one("SELECT * FROM test WHERE id = 1")
    assert result == [{"id": 1, "name": "John Doe"}]


def test_fetch_one_with_no_match_returns_none(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    result = connection.fetch_one("SELECT * FROM test WHERE id = 99")
    assert result is None


def test_fetch_all_returns_all_matching_records(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    connection.execute("INSERT INTO test (name) VALUES ('Jane Doe')")
    result = connection.fetch_all("SELECT * FROM test")
    assert len(result) == 2
    assert result[0]["name"] == "John Doe"
    assert result[1]["name"] == "Jane Doe"


def test_execute_returns_affected_rows(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    affected_rows = connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    assert affected_rows == 1


def test_commit_persists_changes(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    connection.commit()
    result = connection.fetch_one("SELECT * FROM test WHERE id = 1")
    assert result == [{"id": 1, "name": "John Doe"}]


def test_rollback_reverts_changes(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    connection.rollback()
    result = connection.fetch_one("SELECT * FROM test WHERE id = 1")
    assert result is None


def test_close_closes_connection_and_cursor(mock_config):
    connection = Connection.from_config(mock_config)
    connection.close()
    assert connection.conn is None
    assert connection.cursor is None


def test_execute_with_params(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES (?)", ("John Doe",))
    result = connection.fetch_one("SELECT * FROM test WHERE id = 1")
    assert result == [{"id": 1, "name": "John Doe"}]
