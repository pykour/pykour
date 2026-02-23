"""Transaction management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

from pykour.db.sql_utils import validate_identifier

if TYPE_CHECKING:
    from pykour.db.database import Database
    from pykour.db.drivers.base import BaseDriver


class Transaction:
    """Database transaction context manager.

    Example:
        async with db.transaction() as tx:
            await db.insert("users").values(name="Alice").execute()
            # Automatically commits on success, rolls back on exception
    """

    def __init__(
        self,
        database: "Database",
        driver: "BaseDriver",
        conn: Any,
        release_func: Any,
        isolation_level: str | None = None,
    ) -> None:
        self._database = database
        self._driver = driver
        self._conn = conn
        self._release_func = release_func
        self._isolation_level = isolation_level
        self._committed = False
        self._rolled_back = False

    async def __aenter__(self) -> Self:
        """Enter transaction context."""
        await self._driver.begin(self._conn, isolation_level=self._isolation_level)
        # Set the transaction connection on the database
        self._database._set_transaction_connection(self._conn)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit transaction context."""
        try:
            if exc_type is not None:
                # Exception occurred, rollback
                if not self._rolled_back:
                    await self.rollback()
            elif not self._committed and not self._rolled_back:
                # No exception and not explicitly committed/rolled back
                await self.commit()
        finally:
            # Clear the transaction connection
            self._database._clear_transaction_connection()
            # Always release the connection
            await self._release_func(self._conn)

    async def commit(self) -> None:
        """Explicitly commit the transaction."""
        if self._rolled_back:
            raise RuntimeError("Cannot commit: transaction already rolled back")
        if self._committed:
            return
        await self._driver.commit(self._conn)
        self._committed = True

    async def rollback(self) -> None:
        """Explicitly rollback the transaction."""
        if self._committed:
            raise RuntimeError("Cannot rollback: transaction already committed")
        if self._rolled_back:
            return
        await self._driver.rollback(self._conn)
        self._rolled_back = True

    @property
    def connection(self) -> Any:
        """Get the underlying connection for this transaction."""
        return self._conn

    # Savepoint support

    async def savepoint(self, name: str) -> None:
        """Create a savepoint within the transaction.

        Args:
            name: Savepoint name (must be valid SQL identifier).

        Example:
            async with await db.transaction() as tx:
                await db.insert("users").values(name="Alice").execute()
                await tx.savepoint("before_update")
                try:
                    await db.update("users").set(status="active").execute()
                except Exception:
                    await tx.rollback_to("before_update")
        """
        if self._committed or self._rolled_back:
            raise RuntimeError("Cannot create savepoint: transaction already ended")
        validate_identifier(name, "savepoint")
        await self._conn.execute(f"SAVEPOINT {name}")

    async def rollback_to(self, name: str) -> None:
        """Rollback to a savepoint.

        Args:
            name: Savepoint name to rollback to.

        Note:
            The transaction remains active after rolling back to a savepoint.
            The savepoint and any savepoints created after it are released.
        """
        if self._committed or self._rolled_back:
            raise RuntimeError(
                "Cannot rollback to savepoint: transaction already ended"
            )
        validate_identifier(name, "savepoint")
        await self._conn.execute(f"ROLLBACK TO SAVEPOINT {name}")

    async def release_savepoint(self, name: str) -> None:
        """Release (remove) a savepoint.

        Args:
            name: Savepoint name to release.

        Note:
            Once released, you cannot rollback to this savepoint.
            This is optional - savepoints are automatically released on commit.
        """
        if self._committed or self._rolled_back:
            raise RuntimeError("Cannot release savepoint: transaction already ended")
        validate_identifier(name, "savepoint")
        await self._conn.execute(f"RELEASE SAVEPOINT {name}")
