import typing
from collections import defaultdict


class Headers:
    def __init__(self, raw: typing.Iterable[typing.Tuple[bytes, bytes]]) -> None:
        self._headers: dict[str, list[str]] = defaultdict(list)

        for name, value in raw:
            key = name.decode("latin1").lower()
            val = value.decode("latin1")
            self._headers[key].append(val)

    def get(self, key: str) -> list[str] | None:
        return self._headers.get(key.lower(), None)

    def get_first(self, key: str, default: str | None = None) -> str | None:
        values = self.get(key)
        return values[0] if values else default

    def add(self, key: str, value: str) -> None:
        self._headers[key.lower()].append(value)

    def extend(self, key: str, values: typing.Iterable[str]) -> None:
        self._headers[key.lower()].extend(values)

    def update(self, other: typing.Self | dict[str, str | list[str]]) -> None:
        if isinstance(other, Headers):
            for key in other:
                self.extend(key, other.get(key))
        elif isinstance(other, dict):
            for key, value in other.items():
                if isinstance(value, list):
                    self.extend(key, value)
                else:
                    self.add(key, value)
        else:
            raise TypeError(f"Unsupported type for update(): {type(other)}")

    def clear(self) -> None:
        self._headers.clear()

    def copy(self) -> typing.Self:
        new = type(self)([])
        for key, values in self._headers.items():
            new._headers[key] = values.copy()
        return new

    def keys(self) -> typing.Iterable[str]:
        return self._headers.keys()

    def values(self) -> typing.Iterable[str]:
        return (", ".join(v) for v in self._headers.values())

    def items(self) -> typing.Iterable[tuple[str, str]]:
        return ((k, ", ".join(v)) for k, v in self._headers.items())

    def as_list(self) -> list[tuple[bytes, bytes]]:
        result = []
        for k, v_list in self._headers.items():
            for v in v_list:
                result.append((k.encode("latin1"), v.encode("latin1")))
        return result

    def __getitem__(self, key: str) -> str:
        key = key.lower()
        if key not in self._headers:
            raise KeyError(key)
        return ", ".join(self._headers[key])

    def __setitem__(self, key: str, value: str | list[str]) -> None:
        if isinstance(value, str):
            self._headers[key.lower()] = [value]
        else:
            self._headers[key.lower()] = list(value)

    def __delitem__(self, key: str) -> None:
        del self._headers[key.lower()]

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return key.lower() in self._headers

    def __iter__(self) -> typing.Iterator[str]:
        return iter(self._headers)

    def __len__(self) -> int:
        return len(self._headers)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Headers):
            return NotImplemented
        if set(self._headers.keys()) != set(other._headers.keys()):
            return False
        for key in self._headers:
            if sorted(self._headers[key]) != sorted(other._headers.get(key, [])):
                return False
        return True

    def __bool__(self) -> bool:
        return bool(self._headers)

    def __str__(self) -> str:
        lines = [f"{k.title()}: {', '.join(v)}" for k, v in self._headers.items()]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._headers!r})"
