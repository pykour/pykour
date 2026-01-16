"""Validation error types and formatting."""

from dataclasses import dataclass
from typing import Any


@dataclass
class ErrorDetail:
    """Single validation error detail."""

    loc: tuple[str, ...]
    msg: str
    type: str
    input: Any = None


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, errors: list[ErrorDetail]) -> None:
        self.errors = errors
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        count = len(self.errors)
        return f"{count} validation error{'s' if count != 1 else ''}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "error": "Validation Error",
            "detail": [
                {
                    "loc": list(err.loc),
                    "msg": err.msg,
                    "type": err.type,
                }
                for err in self.errors
            ],
        }
