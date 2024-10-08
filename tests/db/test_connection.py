from unittest.mock import MagicMock

import pytest
from pykour.db.connection import ConnectionFactory
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
    connection = ConnectionFactory.create_connection(mock_config)
    assert connection.conn is not None


def test_connection_initialization_with_mysql_succeeds(mocker, mock_config_mysql):
    mocker.patch("mysql.connector.connect", return_value=MagicMock())
    connection = ConnectionFactory.create_connection(mock_config_mysql)
    assert connection.conn is not None


def test_connection_initialization_with_postgres_succeeds(mocker, mock_config_postgres):
    mocker.patch("psycopg2.connect", return_value=MagicMock())
    connection = ConnectionFactory.create_connection(mock_config_postgres)
    assert connection.conn is not None


def test_connection_initialization_with_unsupported_db_type_raises_error(mock_config_unsupported_type):
    with pytest.raises(ValueError):
        ConnectionFactory.create_connection(mock_config_unsupported_type)


def test_fetch_one_returns_correct_data(mocker, mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    result = connection.fetch_one("SELECT * FROM test WHERE id = 1")
    assert result == {"id": 1, "name": "John Doe"}


def test_fetch_one_with_no_match_returns_none(mocker, mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    result = connection.fetch_one("SELECT * FROM test WHERE id = 99")
    assert result is None


def test_fetch_all_returns_all_matching_records(mocker, mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    connection.execute("INSERT INTO test (name) VALUES ('Jane Doe')")
    result = connection.fetch_many("SELECT * FROM test")
    assert len(result) == 2
    assert result[0]["name"] == "John Doe"
    assert result[1]["name"] == "Jane Doe"


def test_execute_returns_affected_rows(mocker, mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    affected_rows = connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    assert affected_rows == 1


def test_commit_persists_changes(mocker, mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    connection.commit()
    result = connection.fetch_one("SELECT * FROM test WHERE id = 1")
    assert result == {"id": 1, "name": "John Doe"}


def test_rollback_reverts_changes(mocker, mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES ('John Doe')")
    connection.rollback()
    result = connection.fetch_one("SELECT * FROM test WHERE id = 1")
    assert result is None


def test_close_closes_connection_and_cursor(mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    connection.close()
    assert connection.conn is None
    assert connection.cursor is None


def test_execute_with_params(mocker, mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    connection.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    connection.execute("INSERT INTO test (name) VALUES (?)", "John Doe")
    result = connection.fetch_one("SELECT * FROM test WHERE id = 1")
    assert result == {"id": 1, "name": "John Doe"}


def test_fetch_one_raises_database_operation_error(mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    with pytest.raises(DatabaseOperationError):
        connection.fetch_one("SELECT * FROM test WHERE id = 1")


def test_fetch_many_raises_database_operation_error(mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    with pytest.raises(DatabaseOperationError):
        connection.fetch_many("SELECT * FROM test WHERE id = 1")


def test_execute_raises_database_operation_error(mock_config):
    connection = ConnectionFactory.create_connection(mock_config)
    with pytest.raises(DatabaseOperationError):
        connection.execute("SELECT * FROM test WHERE id = 1")


def test_execute_mysql(mocker, mock_config_mysql):
    driver = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    mocker.patch("importlib.import_module", return_value=driver)
    conn.cursor.return_value = cursor
    driver.connect.return_value = conn
    connection = ConnectionFactory.create_connection(mock_config_mysql)
    connection.execute("SELECT * FROM test WHERE id = ?", 1)
    cursor.execute.assert_called_with("SELECT * FROM test WHERE id = ?", (1,))


def test_execute_postgresql(mocker, mock_config_postgres):
    driver = MagicMock()
    conn = MagicMock()
    cursor = MagicMock()
    mocker.patch("importlib.import_module", return_value=driver)
    conn.cursor.return_value = cursor
    driver.connect.return_value = conn
    connection = ConnectionFactory.create_connection(mock_config_postgres)
    connection.execute("SELECT * FROM test WHERE id = ?", 1)
    cursor.execute.assert_called_with("SELECT * FROM test WHERE id = %s", (1,))
