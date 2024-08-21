from queue import Queue, Empty, Full
from threading import Lock

from pykour.config import Config
from pykour.db.connection import Connection, ConnectionFactory


class ConnectionPool:
    """Connection pool for database connections."""

    def __init__(self, config: Config):
        self.config = config
        self.max_connections = config.get_datasource_pool_max_connections()
        self.pool: Queue = Queue(maxsize=self.max_connections)
        self.lock = Lock()
        for _ in range(self.max_connections):
            self.pool.put(self._create_new_connection())

    def get_connection(self):
        try:
            return self.pool.get_nowait()
        except Empty:
            with self.lock:
                return self._create_new_connection()

    def release_connection(self, connection):
        try:
            self.pool.put_nowait(connection)
        except Full:
            connection.close()

    def close_all_connections(self):
        while not self.pool.empty():
            conn = self.pool.get_nowait()
            conn.close()

    def _create_new_connection(self) -> Connection:
        return ConnectionFactory.create_connection(self.config)

    def __del__(self):
        self.close_all_connections()
