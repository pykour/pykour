"""Configuration classes for CRUD auto-generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pykour.db.migrations.table import Table


@dataclass
class ListConfig:
    """Configuration for list endpoint."""

    default_limit: int = 20
    max_limit: int = 100
    sortable_fields: list[str] | None = None
    filterable_fields: list[str] | None = None


@dataclass
class CRUDConfig:
    """Configuration for CRUD endpoints."""

    path: str
    table: type[Table]
    operations: list[str] = field(
        default_factory=lambda: ["list", "get", "create", "update", "delete"]
    )
    list_config: ListConfig = field(default_factory=ListConfig)
    id_field: str | None = None
    exclude_fields: list[str] = field(default_factory=list)
    readonly_fields: list[str] = field(default_factory=list)
