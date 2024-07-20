import importlib

from pykour import Config


class Session:
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

    def execute(self, query, params=None):
        if params:
            self.cursor.execute(query, params)
        else:
            self.cursor.execute(query)

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

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
