from __future__ import annotations

from abc import ABCMeta
from typing import Any, Dict, Type, List, Tuple, Optional

from pykour.db import Connection


class BaseModelMetaclass(ABCMeta):

    def __new__(mcs, cls_name: str, bases, attrs, **kwargs: Any) -> type:
        fields = {key: value for key, value in attrs.items() if not key.startswith("_")}

        cls = super().__new__(mcs, cls_name, bases, attrs, **kwargs)
        cls.__fields__ = fields  # type: ignore[attr-defined]
        return cls


class QueryBuilder:
    def __init__(self, model: Type[BaseModel], connection: Connection):
        self.model = model
        self.connection = connection
        self._where_clauses: List[str] = []
        self._params: List[Any] = []

    def where(self, condition: str, *params: Any) -> QueryBuilder:
        self._where_clauses.append(condition)
        self._params.extend(params)
        return self

    def build_query(self) -> Tuple[str, List[Any]]:
        where_clause = " AND ".join(self._where_clauses) if self._where_clauses else "1=1"
        query = f"SELECT * FROM {self.model.__tablename__} WHERE {where_clause}"
        return query, self._params

    def all(self) -> List[BaseModel]:
        query, params = self.build_query()
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [
            self.model(**{col: row[idx] for idx, col in enumerate(["id"] + list(self.model.__fields__.keys()))})
            for row in rows
        ]

    def first(self) -> Optional[BaseModel]:
        query, params = self.build_query()
        cursor = self.connection.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        if row:
            return self.model(**{col: row[idx] for idx, col in enumerate(["id"] + list(self.model.__fields__.keys()))})
        return None


class BaseModel(metaclass=BaseModelMetaclass):
    __tablename__: str
    __fields__: Dict[str, Any]

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.__fields__:
                setattr(self, key, value)

    @classmethod
    def create_table(cls, connection: Connection):
        fields = ", ".join([f"{name} {ftype}" for name, ftype in cls.__fields__.items()])
        query = f"CREATE TABLE IF NOT EXISTS {cls.__tablename__} (id INTEGER PRIMARY KEY, {fields})"
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()

    def save(self, connection: Connection):
        fields = ", ".join(self.__fields__.keys())
        placeholders = ", ".join(["?" for _ in self.__fields__.keys()])
        values = tuple(getattr(self, key) for key in self.__fields__.keys())
        query = f"INSERT INTO {self.__tablename__} ({fields}) VALUES ({placeholders})"
        cursor = connection.cursor()
        cursor.execute(query, values)
        self.id = cursor.lastrowid  # type: ignore[attr-defined]

    @classmethod
    def select(cls, connection: Connection) -> QueryBuilder:
        return QueryBuilder(cls, connection)

    @classmethod
    def all(cls, connection: Connection) -> list[BaseModel]:
        query = f"SELECT * FROM {cls.__tablename__}"
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        return [cls(**{col: row[idx] for idx, col in enumerate(["id"] + list(cls.__fields__.keys()))}) for row in rows]

    def update(self, connection: Connection):
        fields = ", ".join([f"{key} = ?" for key in self.__fields__.keys()])
        values = tuple(getattr(self, key) for key in self.__fields__.keys()) + (self.id,)
        query = f"UPDATE {self.__tablename__} SET {fields} WHERE id = ?"
        connection.execute(query, values)

    def delete(self, connection: Connection):
        query = f"DELETE FROM {self.__tablename__} WHERE id = ?"
        connection.execute(query, (self.id,))
