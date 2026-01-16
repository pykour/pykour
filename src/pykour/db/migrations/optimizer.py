"""Migration operation optimizer."""

from __future__ import annotations

from pykour.db.migrations.operations import (
    AddColumn,
    CreateIndex,
    CreateTable,
    DropColumn,
    DropIndex,
    DropTable,
    Operation,
)


class OperationOptimizer:
    """Optimizes migration operations by merging redundant ones."""

    def optimize(self, operations: list[Operation]) -> list[Operation]:
        """Optimize a list of operations.

        Applies the following optimizations:
        - CreateTable + DropTable for same table = remove both
        - CreateTable + AddColumn for same table = merge column into CreateTable
        - AddColumn + DropColumn for same table/column = remove both
        - CreateIndex + DropIndex for same index = remove both

        Args:
            operations: List of operations to optimize.

        Returns:
            Optimized list of operations.
        """
        result = list(operations)

        result = self._remove_create_drop_table_pairs(result)
        result = self._merge_create_table_with_add_columns(result)
        result = self._remove_add_drop_column_pairs(result)
        result = self._remove_create_drop_index_pairs(result)

        return result

    def _remove_create_drop_table_pairs(
        self, operations: list[Operation]
    ) -> list[Operation]:
        """Remove CreateTable + DropTable pairs for the same table."""
        create_tables: dict[str, int] = {}
        to_remove: set[int] = set()

        for i, op in enumerate(operations):
            if isinstance(op, CreateTable):
                create_tables[op.name] = i
            elif isinstance(op, DropTable):
                if op.name in create_tables:
                    to_remove.add(create_tables[op.name])
                    to_remove.add(i)
                    del create_tables[op.name]

        return [op for i, op in enumerate(operations) if i not in to_remove]

    def _merge_create_table_with_add_columns(
        self, operations: list[Operation]
    ) -> list[Operation]:
        """Merge AddColumn operations into preceding CreateTable for same table."""
        result: list[Operation] = []
        create_table_indices: dict[str, int] = {}

        for op in operations:
            if isinstance(op, CreateTable):
                create_table_indices[op.name] = len(result)
                result.append(op)
            elif isinstance(op, AddColumn):
                if op.table in create_table_indices:
                    idx = create_table_indices[op.table]
                    create_op = result[idx]
                    if isinstance(create_op, CreateTable):
                        new_columns = list(create_op.columns) + [op.column]
                        result[idx] = CreateTable(
                            name=create_op.name,
                            columns=new_columns,
                            if_not_exists=create_op.if_not_exists,
                        )
                else:
                    result.append(op)
            else:
                result.append(op)

        return result

    def _remove_add_drop_column_pairs(
        self, operations: list[Operation]
    ) -> list[Operation]:
        """Remove AddColumn + DropColumn pairs for the same table/column."""
        add_columns: dict[tuple[str, str], int] = {}
        to_remove: set[int] = set()

        for i, op in enumerate(operations):
            if isinstance(op, AddColumn):
                key = (op.table, op.column.name)
                add_columns[key] = i
            elif isinstance(op, DropColumn):
                key = (op.table, op.column_name)
                if key in add_columns:
                    to_remove.add(add_columns[key])
                    to_remove.add(i)
                    del add_columns[key]

        return [op for i, op in enumerate(operations) if i not in to_remove]

    def _remove_create_drop_index_pairs(
        self, operations: list[Operation]
    ) -> list[Operation]:
        """Remove CreateIndex + DropIndex pairs for the same index."""
        create_indices: dict[str, int] = {}
        to_remove: set[int] = set()

        for i, op in enumerate(operations):
            if isinstance(op, CreateIndex):
                create_indices[op.name] = i
            elif isinstance(op, DropIndex):
                if op.name in create_indices:
                    to_remove.add(create_indices[op.name])
                    to_remove.add(i)
                    del create_indices[op.name]

        return [op for i, op in enumerate(operations) if i not in to_remove]
