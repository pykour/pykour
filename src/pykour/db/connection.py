import importlib
from typing import Optional, Dict, Any, List, Union

from pykour.config import Config


class Connection:
    def __init__(self, db_type, **kwargs):
        self.db_type = db_type
        self.conn = None
        if self.db_type == "sqlite":
            sqlite3 = importlib.import_module("sqlite3")
            self.conn = sqlite3.connect(kwargs["url"])
        else:
            raise ValueError(f"Unsupported session type: {self.db_type}")

        self.cursor = self.conn.cursor()

    @classmethod
    def from_config(cls, config: Config):
        db_type = config.get_datasource_type()
        url = config.get_datasource_url()
        username = config.get_datasource_username()
        password = config.get_datasource_password()
        return cls(db_type, url=url, username=username, password=password)

    def find(self, query: str, params: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], None]:
        self._execute(query, params)
        row = self.cursor.fetchone()
        if row:
            columns = [desc[0] for desc in self.cursor.description]
            return dict(zip(columns, row))
        return None

    def select(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        self._execute(query, params)
        rows = self.cursor.fetchall()
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        self._execute(query, params)
        return self.cursor.rowcount

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None

    def _execute(self, query, params=None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)
