from __future__ import annotations

import logging
import os
from typing import Any, Union, Optional, List

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from pykour.logging import ACCESS_LEVEL_NO


def replace_placeholders(config: dict):
    for key, value in config.items():
        if isinstance(value, dict):
            replace_placeholders(value)
        elif isinstance(value, str):
            config[key] = os.path.expandvars(value)


class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, config: Config):
        self.config = config

    def on_modified(self, event):
        if event.src_path == self.config.filepath:
            self.config.load()
            print("Config file has been modified. Reloading...")


class Config:
    KEY_PYKOUR_LOGGING_LEVEL = "pykour.logging.level"
    KEY_PYKOUR_DATASOURCE_TYPE = "pykour.datasource.type"
    KEY_PYKOUR_DATASOURCE_HOST = "pykour.datasource.host"
    KEY_PYKOUR_DATASOURCE_DB = "pykour.datasource.db"
    KEY_PYKOUR_DATASOURCE_USERNAME = "pykour.datasource.username"
    KEY_PYKOUR_DATASOURCE_PASSWORD = "pykour.datasource.password"
    KEY_PYKOUR_DATASOURCE_POOL_MAX_CONNECTIONS = "pykour.datasource.pool.max-connections"

    def __init__(self, filepath=None):
        self.config = {}
        self._last_modified = 0.0
        if filepath is not None:
            self.filepath = os.path.abspath(filepath)
            self.load()
            self._setup_watchdog()

    def load(self):
        try:
            with open(self.filepath, "r") as file:
                print(f"Loading config file: {self.filepath}")
                content = yaml.safe_load(file)
                if isinstance(content, str):
                    print("Format of config file is invalid. Expected a yaml format.")
                    content = {}
                else:
                    replace_placeholders(content)
                self.config = content
            self._last_modified = os.path.getmtime(self.filepath)
        except FileNotFoundError:
            print(f"Config file not found: {self.filepath}")

    def reload(self):
        current_mtime = os.path.getmtime(self.filepath)
        if current_mtime > self._last_modified:
            print("Config file has been modified. Reloading...")
            self.load()

    def _setup_watchdog(self):
        event_handler = ConfigFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, path=os.path.dirname(self.filepath), recursive=False)
        self.observer.start()

    def get(self, key: str, default: Union[Any, None] = None):
        keys = key.split(".")
        d = self.config
        for k in keys:
            if k not in d:
                return default
            d = d[k]
        return d

    def get_int(self, key: str, default: Optional[int] = None) -> Optional[int]:
        value = self.get(key, default)
        if value is None:
            return default
        if isinstance(value, (int, float, str)):
            try:
                return int(value)
            except (ValueError, TypeError):
                raise ValueError(f"Cannot cast value of key '{key}' to int: {value}")
        else:
            raise ValueError(f"Cannot cast value of key '{key}' to int: {value}")

    def get_float(self, key: str, default: Optional[float] = None) -> Optional[float]:
        value = self.get(key, default)
        if value is None:
            return default
        if isinstance(value, (int, float, str)):
            try:
                return float(value)
            except (ValueError, TypeError):
                raise ValueError(f"Cannot cast value of key '{key}' to float: {value}")
        else:
            raise ValueError(f"Cannot cast value of key '{key}' to float: {value}")

    def get_log_levels(self) -> List[int]:
        log_levels = self.get(self.KEY_PYKOUR_LOGGING_LEVEL, "INFO, WARN, ERROR")
        level_names = [level.strip().upper() for level in log_levels.split(",")]

        level_numbers = []
        for level_name in level_names:
            try:
                level_number = getattr(logging, level_name)
                level_numbers.append(level_number)
            except AttributeError:
                raise ValueError(f"Unknown log level: {level_name}")

        level_numbers.append(ACCESS_LEVEL_NO)
        return level_numbers

    def get_datasource_type(self) -> str:
        return self.get(self.KEY_PYKOUR_DATASOURCE_TYPE, None)

    def get_datasource_host(self) -> str:
        return self.get(self.KEY_PYKOUR_DATASOURCE_HOST, None)

    def get_datasource_db(self) -> str:
        return self.get(self.KEY_PYKOUR_DATASOURCE_DB, None)

    def get_datasource_username(self) -> str:
        return self.get(self.KEY_PYKOUR_DATASOURCE_USERNAME, None)

    def get_datasource_password(self) -> str:
        return self.get(self.KEY_PYKOUR_DATASOURCE_PASSWORD, None)

    def get_datasource_pool_max_connections(self) -> int:
        return self.get_int(self.KEY_PYKOUR_DATASOURCE_POOL_MAX_CONNECTIONS, 5)

    def __del__(self):
        if hasattr(self, "observer"):
            self.observer.stop()
            self.observer.join()

    def __str__(self):
        return yaml.dump(self.config, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def __repr__(self):
        return self.__str__()
