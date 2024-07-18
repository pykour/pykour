import logging
from unittest.mock import patch, MagicMock

import pytest

from pykour import Request, Response
from pykour.logging import write_access_log, setup_logging, ACCESS_LEVEL_NO, SpecificLevelsFilter, access


@pytest.fixture
def mock_get_logger():
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_get_logger, mock_logger


@pytest.fixture
def mock_logger():
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def mock_request():
    request = MagicMock(spec=Request)
    request.client = "127.0.0.1"
    request.method = "GET"
    request.path = "/test"
    request.scheme = "http"
    request.version = "1.1"
    return request


@pytest.fixture
def mock_response():
    response = MagicMock(spec=Response)
    response.status = 200
    response.content = "response content"
    return response


@pytest.fixture
def mock_response2():
    response = MagicMock(spec=Response)
    response.status = None
    response.content = "response content"
    return response


def test_access():
    with patch.object(logging.Logger, "_log", autospec=True) as mock_log_method:
        # ダミーメッセージと引数
        message = "Test access log"
        args = ()
        kws = {}

        # モックのロガーを作成し、accessメソッドを追加
        logger = logging.getLogger("test")
        logger.access = access.__get__(logger, logging.Logger)

        # access関数を呼び出し
        logger.access(message, *args, **kws)

        # _logメソッドが適切なレベルで呼び出されたかを検証
        mock_log_method.assert_called_once_with(logger, ACCESS_LEVEL_NO, message, args, **kws)


def test_custom_formatter():
    from pykour.logging import CustomFormatter

    formatter = CustomFormatter("%(levelname)s %(asctime)s %(message)s")
    record = logging.LogRecord("name", logging.INFO, "pathname", 1, "test", [], None)
    assert "INFO" in formatter.format(record)
    assert "test" in formatter.format(record)
    assert "T" in formatter.format(record)


def test_custom_formatter_set_datefmt():
    from pykour.logging import CustomFormatter

    formatter = CustomFormatter("%(levelname)s %(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    record = logging.LogRecord("name", logging.INFO, "pathname", 1, "test", [], None)
    assert "INFO" in formatter.format(record)
    assert "test" in formatter.format(record)


def test_specific_levels_filter():
    # テストするログレベルのリスト
    levels = [logging.INFO, logging.ERROR]

    # SpecificLevelsFilterのインスタンスを作成
    filter_instance = SpecificLevelsFilter(levels)

    # 異なるログレベルのレコードを作成
    info_record = MagicMock(levelno=logging.INFO)
    error_record = MagicMock(levelno=logging.ERROR)
    debug_record = MagicMock(levelno=logging.DEBUG)
    warn_record = MagicMock(levelno=logging.WARN)

    # 各レコードに対してfilter関数を呼び出し、結果を検証
    assert filter_instance.filter(info_record) is True, "INFO level should pass the filter"
    assert filter_instance.filter(error_record) is True, "ERROR level should pass the filter"
    assert filter_instance.filter(debug_record) is False, "DEBUG level should not pass the filter"
    assert filter_instance.filter(warn_record) is False, "WARN level should not pass the filter"


def test_setup_logging_default(mock_get_logger):
    mock_get_logger, mock_logger = mock_get_logger

    setup_logging()

    expected_levels = [logging.INFO, logging.WARN, logging.ERROR, ACCESS_LEVEL_NO]
    mock_logger.setLevel.assert_called_with(logging.NOTSET)
    added_handler = mock_logger.addHandler.call_args[0][0]
    assert isinstance(added_handler, logging.StreamHandler)

    assert added_handler.level == logging.NOTSET
    assert any(isinstance(f, SpecificLevelsFilter) for f in added_handler.filters)

    levels_filter = next(f for f in added_handler.filters if isinstance(f, SpecificLevelsFilter))
    assert levels_filter.levels == expected_levels


def test_write_access_log(mock_logger, mock_request, mock_response):
    elapsed_time = 0.123456
    write_access_log(mock_request, mock_response, elapsed_time)
    mock_logger.access.assert_called_once()
    log_message = mock_logger.access.call_args[0][0]

    assert "127.0.0.1" in log_message
    assert "GET" in log_message
    assert "/test" in log_message
    assert "http/1.1" in log_message
    assert "200 OK" in log_message
    assert "16" in log_message
    assert "0.123456" in log_message
