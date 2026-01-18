"""Interactive CLI utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pykour.db.migrations.runner import Migration


def select_migrations(
    migrations: list[Migration],
    groups: dict[str, list[Migration]],
    applied_versions: set[str],
) -> list[Migration]:
    """Interactively select migrations to squash.

    Args:
        migrations: All available migrations.
        groups: Migrations grouped by table name.
        applied_versions: Set of applied migration versions.

    Returns:
        List of selected migrations.

    Raises:
        ImportError: If questionary is not installed.
    """
    try:
        from questionary import Choice, checkbox  # type: ignore[import-not-found]
    except ImportError as e:
        raise ImportError(
            "questionary is required for interactive mode. "
            "Install it with: pip install questionary"
        ) from e

    choices: list[Choice] = []

    sorted_groups = sorted(
        groups.items(),
        key=lambda x: (x[0] == "(no tables)", x[0] == "multiple tables", x[0]),
    )

    for table_name, table_migrations in sorted_groups:
        choices.append(
            Choice(
                title=f"\n  {table_name}\n  {'─' * 40}",
                value=None,
                disabled="",
            )
        )

        sorted_migrations = sorted(
            table_migrations, key=lambda m: m.version, reverse=True
        )

        for m in sorted_migrations:
            if m.version in applied_versions:
                status = "(applied)"
            else:
                status = "(pending)"

            title = f"  {m.version}_{m.name}  {status}"
            choices.append(
                Choice(
                    title=title,
                    value=m,
                )
            )

    selected = checkbox(
        "Select migrations to squash:",
        choices=choices,
        instruction="(↑↓: move, Space: toggle, a: all, i: invert, Enter: confirm)",
    ).ask()

    if selected is None:
        return []

    return [m for m in selected if m is not None]


def confirm_squash(
    migrations: list[Migration],
    pending_versions: list[str],
) -> bool:
    """Confirm squash operation.

    Args:
        migrations: Migrations to squash.
        pending_versions: Versions that are not yet applied.

    Returns:
        True if user confirms, False otherwise.
    """
    try:
        from questionary import confirm  # type: ignore[import-not-found]
    except ImportError:
        return _simple_confirm(migrations, pending_versions)

    if pending_versions:
        print("\n⚠ Warning: The following migrations are not yet applied:")
        for v in pending_versions:
            print(f"  {v}")
        print("\nThe squashed migration will include these pending changes.")

    return confirm("Proceed with squash?", default=False).ask() or False


def _simple_confirm(
    migrations: list[Migration],
    pending_versions: list[str],
) -> bool:
    """Simple confirmation without questionary.

    Args:
        migrations: Migrations to squash.
        pending_versions: Versions that are not yet applied.

    Returns:
        True if user confirms, False otherwise.
    """
    if pending_versions:
        print("\n⚠ Warning: The following migrations are not yet applied:")
        for v in pending_versions:
            print(f"  {v}")
        print("\nThe squashed migration will include these pending changes.")

    response = input("Proceed with squash? [y/N]: ").strip().lower()
    return response in ("y", "yes")


def select_archive_target(
    migrations: list[Migration],
    current_boundary: str | None,
) -> list[Migration]:
    """Interactively select migrations to archive.

    Args:
        migrations: All available migrations.
        current_boundary: Current archive boundary version (if any).

    Returns:
        List of migrations to archive.

    Raises:
        ImportError: If questionary is not installed.
    """
    available = migrations
    if current_boundary:
        available = [m for m in migrations if m.version > current_boundary]

    if not available:
        return []

    try:
        from questionary import Choice, select  # type: ignore[import-not-found]
    except ImportError:
        return _simple_select_archive(available, current_boundary)

    choices: list[Choice] = []

    for m in available:
        choices.append(
            Choice(
                title=f"{m.version}_{m.name}",
                value=m.version,
            )
        )

    if current_boundary:
        print(f"\nCurrent archive boundary: {current_boundary}")
    print("Select a version to archive up to (all migrations up to this version):\n")

    selected_version = select(
        "Archive up to:",
        choices=choices,
        instruction="(↑↓: move, Enter: select)",
    ).ask()

    if selected_version is None:
        return []

    return [m for m in available if m.version <= selected_version]


def _simple_select_archive(
    migrations: list[Migration],
    current_boundary: str | None,
) -> list[Migration]:
    """Simple archive target selection without questionary.

    Args:
        migrations: Available migrations to archive.
        current_boundary: Current archive boundary version (if any).

    Returns:
        List of migrations to archive.
    """
    if current_boundary:
        print(f"\nCurrent archive boundary: {current_boundary}")

    print("\nAvailable migrations:")
    for i, m in enumerate(migrations, 1):
        print(f"  {i}. {m.version}_{m.name}")

    print("\nEnter the number of the migration to archive up to (or 'q' to cancel):")
    response = input("> ").strip()

    if response.lower() in ("q", "quit", ""):
        return []

    try:
        index = int(response) - 1
        if 0 <= index < len(migrations):
            target_version = migrations[index].version
            return [m for m in migrations if m.version <= target_version]
    except ValueError:
        pass

    print("Invalid selection")
    return []
