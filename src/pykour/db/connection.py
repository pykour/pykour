import importlib
import logging
import re
import time
from typing import Dict, Any, List, Union

from pykour.config import Config
from pykour.exceptions import DatabaseOperationError


class Connection:
    def __init__(self, db_type, **kwargs):
        self.db_type = db_type
        self.conn = None
        if self.db_type == "sqlite":
            sqlite3 = importlib.import_module("sqlite3")
            self.conn = sqlite3.connect(kwargs["db"])
        elif self.db_type == "mysql" or self.db_type == "maria":
            pymysql = importlib.import_module("pymysql")
            self.conn = pymysql.connect(
                host=kwargs["host"],
                user=kwargs["username"],
                password=kwargs["password"],
                db=kwargs["db"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
        elif self.db_type == "postgres":
            psycopg2 = importlib.import_module("psycopg2")
            self.conn = psycopg2.connect(
                host=kwargs["host"],
                user=kwargs["username"],
                password=kwargs["password"],
                dbname=kwargs["db"],
            )
        else:
            raise ValueError(f"Unsupported session type: {self.db_type}")

        self.cursor = self.conn.cursor()
        self.is_committed = False
        self.is_rolled_back = False
        self.is_closed = False
        self.logger = logging.getLogger("pykour")

    @classmethod
    def from_config(cls, config: Config):
        db_type = config.get_datasource_type()
        if db_type == "sqlite":
            db = config.get_datasource_db()
            return cls(db_type, db=db)
        elif db_type == "mysql" or db_type == "maria":
            host = config.get_datasource_host()
            db = config.get_datasource_db()
            username = config.get_datasource_username()
            password = config.get_datasource_password()
            return cls(db_type, host=host, db=db, username=username, password=password)
        elif db_type == "postgres":
            host = config.get_datasource_host()
            db = config.get_datasource_db()
            username = config.get_datasource_username()
            password = config.get_datasource_password()
            return cls(db_type, host=host, db=db, username=username, password=password)
        else:
            raise ValueError(f"Unsupported session type: {db_type}")

    def fetch_one(self, query: str, *args) -> Union[Dict[str, Any], None]:
        """Execute a query and return the first row as a dictionary.

        Args:
            query: The SQL query to execute.
            args: The parameters to pass to the query.
        Returns:
            A dictionary representing the first row, or None if no rows are found
        """

        try:
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"==>  Query: {self.format_sql_string(query)}")
                self.logger.debug(f"==> Params: {', '.join(map(str, args))}")
            start_time = time.perf_counter()
            self._execute(query, args)
            row = self.cursor.fetchone()
            end_time = time.perf_counter()
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(
                    f"<== Result: {1 if row else 0} row(s) affected, took {(end_time - start_time) * 1000:.2f} ms"
                )
            if row:
                columns = [desc[0] for desc in self.cursor.description]
                return dict(zip(columns, row))
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
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
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"==>  Query: {self.format_sql_string(query)}")
                self.logger.debug(f"==> Params: {', '.join(map(str, args))}")
            start_time = time.perf_counter()
            self._execute(query, args)
            rows = self.cursor.fetchall()
            end_time = time.perf_counter()
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(
                    f"<== Result: {len(rows)} row(s) affected, took {(end_time - start_time) * 1000:.2f} ms"
                )
            columns = [desc[0] for desc in self.cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
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
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(f"==>  Query: {self.format_sql_string(query)}")
                self.logger.debug(f"==> Params: {', '.join(map(str, args))}")
            start_time = time.perf_counter()
            self._execute(query, args)
            end_time = time.perf_counter()
            rowcount = self.cursor.rowcount
            if rowcount == -1:
                rowcount = 1
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug(
                    f"<== Result: {rowcount} row(s) affected, took {(end_time - start_time) * 1000:.2f} ms"
                )
            return rowcount
        except Exception as e:
            self.logger.error(f"Database operation failed: {e}")
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
        if self.db_type == "postgres":
            # Convert ? to %s for PostgreSQL
            query = query.replace("?", "%s")

        if args:
            self.cursor.execute(query, args)
        else:
            self.cursor.execute(query)

    @staticmethod
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
