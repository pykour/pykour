import logging
from datetime import datetime
from enum import Enum
from http import HTTPStatus

from colorama import Fore, Style

from pykour.request import Request
from pykour.response import Response

LOG_COLORS = {
    "INFO": Fore.GREEN,
    "WARN": Fore.YELLOW,
    "ERROR": Fore.RED,
    "TRACE": Fore.CYAN,
    "ACCESS": Fore.BLUE,
}

STATUS_COLORS = {
    "2xx": Fore.GREEN,
    "3xx": Fore.BLUE,
    "4xx": Fore.YELLOW,
    "5xx": Fore.RED,
}


class LogLevel(Enum):
    TRACE = 1
    INFO = 2
    WARN = 3
    ERROR = 4
    ACCESS = 5


class InterceptHandler(logging.Handler):
    def emit(self, record): ...


TRACE_LEVEL = 5
ACCESS_LEVEL = 25

CUSTOM_LOG_LEVELS = {
    "TRACE": TRACE_LEVEL,
    "ACCESS": ACCESS_LEVEL,
}


def trace(self, message, *args, **kws):
    self._log(TRACE_LEVEL, message, args, **kws)


def access(self, message, *args, **kws):
    self._log(ACCESS_LEVEL, message, args, **kws)


logging.addLevelName(TRACE_LEVEL, "TRACE")
logging.Logger.trace = trace
logging.addLevelName(ACCESS_LEVEL, "ACCESS")
logging.Logger.access = access


class CustomFormatter(logging.Formatter):
    converter = datetime.fromtimestamp

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            try:
                s = dt.isoformat(timespec="milliseconds")
            except TypeError:
                s = dt.isoformat()
        return s + self.format_time_zone()

    @staticmethod
    def format_time_zone():
        utc_offset = datetime.now().astimezone().strftime("%z")
        return utc_offset

    def format(self, record):
        # ログレベル名を6文字に固定
        record.levelname = f"{record.levelname:<6}"
        return super().format(record)


class SpecificLevelsFilter(logging.Filter):
    def __init__(self, levels):
        super().__init__()
        self.levels = levels

    def filter(self, record):
        return record.levelno in self.levels


def setup_logging(log_levels=None) -> None:
    if log_levels is None:
        log_levels = [logging.INFO, logging.WARN, logging.ERROR, ACCESS_LEVEL]

    # Suppress logging from Uvicorn and Gunicorn
    for _logger in ("uvicorn", "uvicorn.error", "uvicorn.access", "gunicorn.error"):
        logging_logger = logging.getLogger(_logger)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.NOTSET)
    level_color = LOG_COLORS.get(LogLevel.ACCESS.name, Fore.WHITE)
    formatter = CustomFormatter(f"{level_color}%(levelname)s{Style.RESET_ALL} [%(asctime)s] %(message)s")
    console_handler.setFormatter(formatter)
    levels_filter = SpecificLevelsFilter(levels=log_levels)
    console_handler.addFilter(levels_filter)

    access_logger = logging.getLogger("pykour.access")
    access_logger.setLevel(logging.NOTSET)
    access_logger.addHandler(console_handler)
    app_logger = logging.getLogger("pykour")
    app_logger.setLevel(logging.NOTSET)
    app_logger.addHandler(console_handler)


def write_access_log(request: Request, response: Response, elapsed: float) -> None:
    """Write access log."""

    logger = logging.getLogger("pykour.access")

    category = f"{response.status // 100}xx"
    category_color = STATUS_COLORS.get(category, Fore.WHITE)

    client = request.client or "-"
    method = request.method or "-"
    path = request.path or "-"
    scheme = request.scheme or "-"
    version = request.version or "-"
    status = response.status or "-"
    if status == "-":
        phrase = "-"
    else:
        phrase = HTTPStatus(status).phrase
    content = response.content or ""

    logger.access(
        f"{client} - - {method} {path} {scheme}/{version} {category_color}{status} {phrase}{Style.RESET_ALL}"
        + f" {len(str(content))} {elapsed:.6f}",
    )
