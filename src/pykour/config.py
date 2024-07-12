from __future__ import annotations

import logging
import os
from typing import Any, Union, Optional

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger("uvicorn.app")


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
            logger.info("Config file has been modified. Reloading...")


class Config:
    def __init__(self, filepath):
        self.filepath = os.path.abspath(filepath)
        self.config = {}
        self._last_modified = 0.0
        self.load()
        self._setup_watchdog()

    def load(self):
        try:
            with open(self.filepath, "r") as file:
                logger.info(f"Loading config file: {self.filepath}")
                content = yaml.safe_load(file)
                if isinstance(content, str):
                    logger.error("Format of config file is invalid. Expected a yaml format.")
                    content = {}
                else:
                    replace_placeholders(content)
                self.config = content
            self._last_modified = os.path.getmtime(self.filepath)
        except FileNotFoundError:
            logger.error(f"Config file not found: {self.filepath}")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")

    def reload(self):
        current_mtime = os.path.getmtime(self.filepath)
        if current_mtime > self._last_modified:
            logger.info("Config file has been modified. Reloading...")
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

    def __del__(self):
        self.observer.stop()
        self.observer.join()

    def __str__(self):
        return yaml.dump(self.config, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def __repr__(self):
        return self.__str__()
