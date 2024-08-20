import logging
from unittest.mock import patch, MagicMock

import pytest

from pykour import Request, Response
from pykour.logging import (
    write_access_log,
    setup_logging,
    ACCESS_LEVEL_NO,
    SpecificLevelsFilter,
    CustomLogger,
    write_info_log,
    write_warn_log,
    write_error_log,
    write_debug_log,
)


@pytest.fixture
def mock_get_logger():
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_get_logger, mock_logger


@pytest.fixture
def mock_executor():
    with patch("concurrent.futures.ThreadPoolExecutor") as mock_executor:
        yield mock_executor


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
        message = "Test access log"
        args = ()
        kws = {}

        logging.setLoggerClass(CustomLogger)
        logger = logging.getLogger("pykour")

        logger.access(message, *args, **kws)

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
    levels = [logging.INFO, logging.ERROR]

    filter_instance = SpecificLevelsFilter(levels)

    info_record = MagicMock(levelno=logging.INFO)
    error_record = MagicMock(levelno=logging.ERROR)
    debug_record = MagicMock(levelno=logging.DEBUG)
    warn_record = MagicMock(levelno=logging.WARN)

    assert filter_instance.filter(info_record) is True, "INFO level should pass the filter"
    assert filter_instance.filter(error_record) is True, "ERROR level should pass the filter"
    assert filter_instance.filter(debug_record) is False, "DEBUG level should not pass the filter"
    assert filter_instance.filter(warn_record) is False, "WARN level should not pass the filter"


def test_setup_logging_default(mock_get_logger):
    mock_get_logger, mock_logger = mock_get_logger

    setup_logging()

    expected_levels = [logging.INFO, logging.WARN, logging.ERROR, ACCESS_LEVEL_NO]
    mock_logger.setLevel.assert_called_with(logging.NOTSET)

    added_handler = mock_logger.handlers[0]
    assert isinstance(added_handler, logging.StreamHandler)

    assert added_handler.level == logging.NOTSET
    assert any(isinstance(f, SpecificLevelsFilter) for f in added_handler.filters)

    levels_filter = next(f for f in added_handler.filters if isinstance(f, SpecificLevelsFilter))
    assert levels_filter.levels == expected_levels


def test_write_info_log():
    with patch("pykour.logging.executor") as mock_executor:
        with patch("pykour.logging.logger") as mock_logger:
            mock_logger.info = MagicMock()
            mock_logger.isEnabledFor.return_value = True
            mock_executor.submit.return_value.result.return_value = None
            write_info_log("Test info log")
            mock_executor.submit.assert_called_once()
            log_message = mock_executor.submit.call_args.args[1]

            assert "Test info log" in log_message


def test_write_warn_log():
    with patch("pykour.logging.executor") as mock_executor:
        with patch("pykour.logging.logger") as mock_logger:
            mock_logger.warn = MagicMock()
            mock_logger.isEnabledFor.return_value = True
            mock_executor.submit.return_value.result.return_value = None
            write_warn_log("Test warn log")
            mock_executor.submit.assert_called_once()
            log_message = mock_executor.submit.call_args.args[1]

            assert "Test warn log" in log_message


def test_write_error_log():
    with patch("pykour.logging.executor") as mock_executor:
        with patch("pykour.logging.logger") as mock_logger:
            mock_logger.error = MagicMock()
            mock_logger.isEnabledFor.return_value = True
            mock_executor.submit.return_value.result.return_value = None
            write_error_log("Test error log")
            mock_executor.submit.assert_called_once()
            log_message = mock_executor.submit.call_args.args[1]

            assert "Test error log" in log_message


def test_write_debug_log():
    with patch("pykour.logging.executor") as mock_executor:
        with patch("pykour.logging.logger") as mock_logger:
            mock_logger.debug = MagicMock()
            mock_logger.isEnabledFor.return_value = True
            mock_executor.submit.return_value.result.return_value = None
            write_debug_log("Test debug log")
            mock_executor.submit.assert_called_once()
            log_message = mock_executor.submit.call_args.args[1]

            assert "Test debug log" in log_message


def test_write_access_log(mock_request, mock_response):
    elapsed_time = 0.123456

    with patch("pykour.logging.executor") as mock_executor:
        with patch("pykour.logging.access_logger") as mock_access_logger:
            mock_access_logger.access = MagicMock()
            mock_executor.submit.return_value.result.return_value = None
            write_access_log(mock_request, mock_response, elapsed_time)
            mock_executor.submit.assert_called_once()
            log_message = mock_executor.submit.call_args.args[1]

            assert "127.0.0.1" in log_message
            assert "GET" in log_message
            assert "/test" in log_message
            assert "http/1.1" in log_message
            assert "200 OK" in log_message
            assert "16" in log_message
            assert "0.123" in log_message


def test_intercept_handler():
    from pykour.logging import InterceptHandler

    handler = InterceptHandler()
    record = logging.LogRecord("name", logging.INFO, "pathname", 1, "test", [], None)
    handler.emit(record)
