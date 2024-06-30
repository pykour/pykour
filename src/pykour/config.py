from __future__ import annotations

import os

import yaml
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, config: Config):
        self.config = config

    def on_modified(self, event):
        if event.src_path == self.config.filepath:
            self.config.load()


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
                self.config = yaml.safe_load(file)
            self._last_modified = os.path.getmtime(self.filepath)
        except FileNotFoundError:
            print(f"Config file not found: {self.filepath}")
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file: {e}")

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

    def get(self, key, default=None):
        keys = key.split(".")
        d = self.config
        for k in keys:
            if k not in d:
                return default
            d = d[k]
        return d

    def __del__(self):
        self.observer.stop()
        self.observer.join()

    def __str__(self):
        return yaml.dump(self.config, default_flow_style=False, allow_unicode=True, sort_keys=False)

    def __repr__(self):
        return self.__str__()
