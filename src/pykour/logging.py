import logging
import re
import threading
from datetime import datetime
from http import HTTPStatus

from colorama import Fore, Style

from pykour.request import Request
from pykour.response import Response

from pykour.globals import thread_local

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


class InterceptHandler(logging.Handler):
    def emit(self, record):
        pass


ACCESS_LEVEL_NO = 25
ACCESS_LEVEL_NAME = "ACCESS"


def access(self, message, *args, **kws):
    self._log(ACCESS_LEVEL_NO, message, args, **kws)


logging.addLevelName(ACCESS_LEVEL_NO, ACCESS_LEVEL_NAME)
logging.Logger.access = access  # type: ignore[attr-defined]


class CustomFormatter(logging.Formatter):
    converter = datetime.fromtimestamp  # type: ignore[assignment]

    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)  # type: ignore[has-type]
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            s = dt.isoformat(timespec="milliseconds")
        return s + self.format_time_zone()

    @staticmethod
    def format_time_zone():
        utc_offset = datetime.now().astimezone().strftime("%z")
        return utc_offset

    def format(self, record):
        record.levelname = f"{record.levelname:<6}"
        request_id = getattr(thread_local, "request_id", threading.get_ident())
        record.request_id = request_id
        return super().format(record)


class SpecificLevelsFilter(logging.Filter):
    def __init__(self, levels):
        super().__init__()
        self.levels = levels

    def filter(self, record):
        return record.levelno in self.levels


class CustomLogger(logging.Logger):
    def __init__(self, name):
        super().__init__(name)
        self.levels = [ACCESS_LEVEL_NO]

    def isEnabledFor(self, level):
        return level in self.levels


def setup_logging(log_levels=None) -> None:
    if log_levels is None:
        log_levels = [logging.INFO, logging.WARN, logging.ERROR, ACCESS_LEVEL_NO]

    # Suppress logging from Uvicorn and Gunicorn
    for _logger in ("uvicorn", "uvicorn.error", "uvicorn.access", "gunicorn.error"):
        logging_logger = logging.getLogger(_logger)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.NOTSET)
    level_color = LOG_COLORS.get(ACCESS_LEVEL_NAME, Fore.WHITE)
    formatter = CustomFormatter(
        f"{level_color}%(levelname)s{Style.RESET_ALL} [%(asctime)s] [%(request_id)s] %(message)s"
    )
    console_handler.setFormatter(formatter)
    levels_filter = SpecificLevelsFilter(levels=log_levels)
    console_handler.addFilter(levels_filter)

    logging.setLoggerClass(CustomLogger)

    logger = logging.getLogger("pykour")
    logger.setLevel(logging.NOTSET)
    logger.addHandler(console_handler)

    logger.levels = log_levels  # type: ignore[attr-defined]


def write_access_log(request: Request, response: Response, elapsed: float) -> None:
    """Write access log."""

    logger = logging.getLogger("pykour.access")

    category = f"{response.status // 100}xx"
    category_color = STATUS_COLORS.get(category, Fore.WHITE)

    client = request.client or "-"
    method = request.method or "-"
    path = request.path or "-"
    path = re.sub(r"/+", "/", path)
    scheme = request.scheme or "-"
    version = request.version or "-"
    status = response.status
    phrase = HTTPStatus(response.status).phrase
    content = response.content or ""

    logger.access(  # type: ignore[attr-defined]
        f"{client} - - {method} {path} {scheme}/{version} {category_color}{status} {phrase}{Style.RESET_ALL}"
        + f" {len(str(content))} {elapsed:.6f}",
    )
