"""Migration exceptions."""


class MigrationError(Exception):
    """Base exception for migration errors."""


class MigrationNotFoundError(MigrationError):
    """Migration file not found."""

    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(f"Migration not found: {version}")


class MigrationAlreadyAppliedError(MigrationError):
    """Migration has already been applied."""

    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(f"Migration already applied: {version}")


class MigrationNotAppliedError(MigrationError):
    """Migration has not been applied."""

    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(f"Migration not applied: {version}")


class InvalidMigrationError(MigrationError):
    """Migration file is invalid."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid migration {path}: {reason}")


class OperationError(MigrationError):
    """Error executing a migration operation."""


class SchemaIntrospectionError(MigrationError):
    """Error reading database schema."""


class SquashError(MigrationError):
    """Error during migration squashing."""


class SquashRangeError(SquashError):
    """Invalid squash range."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ArchiveBoundaryError(MigrationError):
    """Cannot perform operation past archive boundary."""

    def __init__(self, boundary: str, message: str | None = None) -> None:
        self.boundary = boundary
        if message is None:
            message = f"Cannot perform operation past archive boundary ({boundary})"
        super().__init__(message)
