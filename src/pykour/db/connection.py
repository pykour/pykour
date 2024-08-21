from __future__ import annotations
import abc
import importlib
import re
import time
from typing import Dict, Any, List, Union

from pykour.config import Config
from pykour.exceptions import DatabaseOperationError
from pykour.logging import write_debug_log, write_error_log


def format_sql_string(sql: str) -> str:
    """
    Formats an SQL string by replacing newlines and tabs with spaces,
    then reducing multiple consecutive spaces to a single space.

    Args:
    sql (str): The input SQL string to format.

    Returns:
    str: The formatted SQL string.
    """
    # Step 1: Replace newlines and tabs with spaces
    sql = re.sub(r"[\n\t]", " ", sql)

    # Step 2: Replace multiple spaces with a single space
    sql = re.sub(r"\s+", " ", sql)

    return sql.strip()  # Remove leading/trailing whitespace


class Connection(abc.ABC):
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.is_committed = False
        self.is_rolled_back = False
        self.is_closed = False

    @abc.abstractmethod
    def connect(self, host=None, db=None, username=None, password=None) -> Connection:
        """Connect to the database."""
        pass  # pragma: no cover

    @abc.abstractmethod
    def preprocess_query(self, query: str) -> str:
        """Preprocess the query before execution."""
        pass  # pragma: no cover

    def fetch_one(self, query: str, *args) -> Union[Dict[str, Any], None]:
        """Execute a query and return the first row as a dictionary.

        Args:
            query: The SQL query to execute.
            args: The parameters to pass to the query.
        Returns:
            A dictionary representing the first row, or None if no rows are found
        """
        try:
            write_debug_log(f"==>  Query: {format_sql_string(query)}")
            write_debug_log(f"==> Params: {', '.join(map(str, args))}")
            start_time = time.perf_counter()
            self._execute(query, args)
            row = self.cursor.fetchone()
            end_time = time.perf_counter()
            write_debug_log(
                f"<== Result: {1 if row else 0} row(s) affected, took {(end_time - start_time) * 1000:.2f} ms"
            )
            if row:
                columns = [desc[0] for desc in self.cursor.description]
                return dict(zip(columns, row))
        except Exception as e:
            write_error_log(f"Database operation failed: {e}")
            raise DatabaseOperationError(caused_by=e)
        return None

    def fetch_many(self, query: str, *args) -> List[Dict[str, Any]]:
        """Execute a query and return all rows as a list of dictionaries.

        Args:
            query: The SQL query to execute.
            args: The parameters to pass to the query.
        Returns:
            A list of dictionaries representing the rows.
        """
        try:
            write_debug_log(f"==>  Query: {format_sql_string(query)}")
            write_debug_log(f"==> Params: {', '.join(map(str, args))}")
            start_time = time.perf_counter()
            self._execute(query, args)
            rows = self.cursor.fetchall()
            end_time = time.perf_counter()
            write_debug_log(f"<== Result: {len(rows)} row(s) affected, took {(end_time - start_time) * 1000:.2f} ms")
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            write_error_log(f"Database operation failed: {e}")
            raise DatabaseOperationError(caused_by=e)

    def execute(self, query: str, *args) -> int:
        """Execute a query and return the number of affected rows.

        Args:
            query: The SQL query to execute.
            args: The parameters to pass to the query.
        Returns:
            The number of affected rows.
        """
        try:
            write_debug_log(f"==>  Query: {format_sql_string(query)}")
            write_debug_log(f"==> Params: {', '.join(map(str, args))}")
            start_time = time.perf_counter()
            self._execute(query, args)
            end_time = time.perf_counter()
            rowcount = self.cursor.rowcount
            if rowcount == -1:
                rowcount = 1
            write_debug_log(f"<== Result: {rowcount} row(s) affected, took {(end_time - start_time) * 1000:.2f} ms")
            return rowcount
        except Exception as e:
            write_error_log(f"Database operation failed: {e}")
            raise DatabaseOperationError(caused_by=e)

    def commit(self):
        """Commit the transaction."""
        self.conn.commit()
        self.is_committed = True

    def rollback(self):
        """Rollback the transaction."""
        self.conn.rollback()
        self.is_rolled_back = True

    def close(self):
        """Close the connection and cursor."""
        if self.cursor:
            self.cursor.close()
            self.cursor = None
        if self.conn:
            self.conn.close()
            self.conn = None
        self.is_closed = True

    def _execute(self, query, args=None):
        query = self.preprocess_query(query)

        if args:
            self.cursor.execute(query, args)
        else:
            self.cursor.execute(query)


class SQLiteConnection(Connection):
    def connect(self, host=None, db=None, username=None, password=None) -> Connection:
        sqlite3 = importlib.import_module("sqlite3")
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()

        return self

    def preprocess_query(self, query: str) -> str:
        return query


class MySQLConnection(Connection):
    def connect(self, host=None, db=None, username=None, password=None) -> Connection:
        mysql = importlib.import_module("mysql.connector")
        self.conn = mysql.connect(
            host=host,
            user=username,
            password=password,
            database=db,
            charset="utf8mb4",
        )
        self.cursor = self.conn.cursor()

        return self

    def preprocess_query(self, query: str) -> str:
        return query


class PostgreSQLConnection(Connection):
    def connect(self, host=None, db=None, username=None, password=None) -> Connection:
        psycopg2 = importlib.import_module("psycopg2")
        self.conn = psycopg2.connect(
            host=host,
            user=username,
            password=password,
            dbname=db,
        )
        self.cursor = self.conn.cursor()

        return self

    def preprocess_query(self, query: str) -> str:
        return query.replace("?", "%s")


class ConnectionFactory:
    @staticmethod
    def create_connection(config: Config) -> Connection:
        db_type = config.get_datasource_type()
        conn: Connection
        if db_type == "sqlite":
            conn = SQLiteConnection()
        elif db_type == "mysql" or db_type == "maria":
            conn = MySQLConnection()
        elif db_type == "postgres":
            conn = PostgreSQLConnection()
        else:
            raise ValueError(f"Unsupported session type: {db_type}")

        return conn.connect(
            host=config.get_datasource_host(),
            db=config.get_datasource_db(),
            username=config.get_datasource_username(),
            password=config.get_datasource_password(),
        )
