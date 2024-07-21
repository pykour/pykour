import pytest
from unittest.mock import MagicMock, patch

from pykour.db.pool import ConnectionPool
from pykour.config import Config


@pytest.fixture
def mock_config():
    config = MagicMock(spec=Config)
    config.get_datasource_pool_max_connections.return_value = 2
    return config


@pytest.fixture
def mock_connection():
    with patch("pykour.db.pool.Connection") as mock:
        yield mock


def test_connection_pool_with_mocked_connection(mock_config, mock_connection):
    pool = ConnectionPool(mock_config)
    return pool


def test_getting_connection_returns_connection_from_pool(mock_config, mock_connection):
    pool = ConnectionPool(mock_config)
    connection = pool.get_connection()
    assert connection is not None


def test_releasing_connection_puts_it_back_to_pool_if_not_full(mock_config, mock_connection):
    pool = ConnectionPool(mock_config)
    connection = pool.get_connection()
    pool.release_connection(connection)
    assert pool.pool.qsize() == 2


def test_releasing_connection_closes_it_if_pool_is_full(mock_config, mock_connection):
    pool = ConnectionPool(mock_config)
    pool.release_connection(mock_connection)
    mock_connection.close.assert_called_once()


def test_getting_connection_creates_new_if_pool_is_empty_and_max_not_reached(mock_config, mock_connection):
    mock_config.get_datasource_pool_max_connections.return_value = 3
    pool = ConnectionPool(mock_config)
    pool.get_connection()
    pool.get_connection()
    assert pool.pool.qsize() == 1


def test_closing_all_connections_closes_each_connection(mock_config, mock_connection):
    pool = ConnectionPool(mock_config)
    pool.close_all_connections()
    for _ in range(mock_config.get_datasource_pool_max_connections.return_value):
        mock_connection.from_config.assert_called_with(mock_config)
        mock_connection.from_config.return_value.close.assert_called()


def test_create_connection_when_pool_is_empty(mock_config, mock_connection):
    pool = ConnectionPool(mock_config)
    pool.get_connection()
    pool.get_connection()
    pool.get_connection()
    mock_connection.from_config.assert_called_with(mock_config)
