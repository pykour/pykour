"""Query result types."""

from typing import Any


class Row(dict[str, Any]):
    """A single row from a query result.

    Provides both dict-style and attribute-style access to column values.

    Example:
        row = Row({"id": 1, "name": "Alice"})
        assert row["id"] == 1
        assert row.name == "Alice"
    """

    def __getattr__(self, name: str) -> Any:
        """Allow attribute-style access to column values."""
        try:
            return self[name]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    def __setattr__(self, name: str, value: Any) -> None:
        """Allow attribute-style setting of column values."""
        self[name] = value

    def __delattr__(self, name: str) -> None:
        """Allow attribute-style deletion of column values."""
        try:
            del self[name]
        except KeyError:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            ) from None

    def __repr__(self) -> str:
        """Return a string representation of the row."""
        items = ", ".join(f"{k}={v!r}" for k, v in self.items())
        return f"Row({items})"
