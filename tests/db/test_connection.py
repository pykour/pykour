from unittest.mock import MagicMock

import pytest
from pykour.db.connection import Connection
from pykour.config import Config
from pykour.exceptions import DatabaseOperationError


@pytest.fixture
def mock_config():
    config = Config()
    config.config = {
        "pykour": {
            "datasource": {
                "type": "sqlite",
                "db": "file::memory:",
            }
        }
    }
    return config


@pytest.fixture
def mock_config_mysql():
    config = Config()
    config.config = {
        "pykour": {
            "datasource": {
                "type": "mysql",
                "host": "localhost",
                "db": "test",
                "username": "user",
                "password": "pass",
            }
        }
    }
    return config


@pytest.fixture
def mock_config_postgres():
    config = Config()
    config.config = {
        "pykour": {
            "datasource": {
                "type": "postgres",
                "host": "localhost",
                "db": "test",
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


def test_connection_initialization_with_sqlite_succeeds(mocker, mock_config):
    mocker.patch("sqlite3.connect", return_value=MagicMock())
    connection = Connection.from_config(mock_config)
    assert connection.db_type == "sqlite"
    assert connection.conn is not None


def test_connection_initialization_with_mysql_succeeds(mocker, mock_config_mysql):
    mocker.patch("pymysql.connect", return_value=MagicMock())
    connection = Connection.from_config(mock_config_mysql)
    assert connection.db_type == "mysql"
    assert connection.conn is not None


def test_connection_initialization_with_postgres_succeeds(mocker, mock_config_postgres):
    mocker.patch("psycopg2.connect", return_value=MagicMock())
    connection = Connection.from_config(mock_config_postgres)
    assert connection.db_type == "postgres"
    assert connection.conn is not None


def test_connection_initialization_with_unsupported_db_type_raises_error(mock_config_unsupported_type):
    with pytest.raises(ValueError):
        Connection.from_config(mock_config_unsupported_type)

    with pytest.raises(ValueError):
        Connection("unsupported_db")


def test_fetch_one_returns_correct_data(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    result = connection.find_one("SELECT * FROM test WHERE id = 1")
    assert result == {"id": 1, "name": "John Doe"}


def test_fetch_one_with_no_match_returns_none(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    result = connection.find_one("SELECT * FROM test WHERE id = 99")
    assert result is None


def test_fetch_all_returns_all_matching_records(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    connection.execute("INSERT INTO test (name) VALUES ('Jane Doe')")
    result = connection.find_many("SELECT * FROM test")
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
    result = connection.find_one("SELECT * FROM test WHERE id = 1")
    assert result == {"id": 1, "name": "John Doe"}


def test_rollback_reverts_changes(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    connection.rollback()
    result = connection.find_one("SELECT * FROM test WHERE id = 1")
    assert result is None


def test_close_closes_connection_and_cursor(mock_config):
    connection = Connection.from_config(mock_config)
    connection.close()
    assert connection.conn is None
    assert connection.cursor is None


def test_execute_with_params(mock_config):
    connection = Connection.from_config(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES (?)", "John Doe")
    result = connection.find_one("SELECT * FROM test WHERE id = 1")
    assert result == {"id": 1, "name": "John Doe"}


def test_find_one_raises_database_operation_error(mock_config):
    connection = Connection.from_config(mock_config)
    with pytest.raises(DatabaseOperationError):
        connection.find_one("SELECT * FROM test WHERE id = 1")


def test_find_many_raises_database_operation_error(mock_config):
    connection = Connection.from_config(mock_config)
    with pytest.raises(DatabaseOperationError):
        connection.find_many("SELECT * FROM test WHERE id = 1")


def test_execute_raises_database_operation_error(mock_config):
    connection = Connection.from_config(mock_config)
    with pytest.raises(DatabaseOperationError):
        connection.execute("SELECT * FROM test WHERE id = 1")


def test_execute_when_type_is_postgres(mocker):
    driver = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    driver.connect.return_value = conn

    mocker.patch("importlib.import_module", return_value=driver)
    connection = Connection(db_type="postgres", host="localhost", db="test", username="user", password="pass")

    connection.execute("SELECT * FROM test WHERE id = ?", 1)
    cursor.execute.assert_called_once_with("SELECT * FROM test WHERE id = %s", (1,))
