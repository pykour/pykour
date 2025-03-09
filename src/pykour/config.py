from __future__ import annotations

from typing import Any


class Config:

    def __init__(self):
        self.config = {}

    def __getitem__(self, key: str) -> Any:
        return self.config[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.config[key] = value
