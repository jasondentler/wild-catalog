import sqlite3
from pathlib import Path
from typing import Protocol


class SpeciesRangeStore(Protocol):
    def get_present_taxon_ids_for_cell(self, h3_cell: str) -> set[int]:
        ...

    def contains_taxon_in_cell(self, *, h3_cell: str, taxon_id: int) -> bool:
        ...

    def get_h3_resolution(self) -> int:
        ...


class SQLiteSpeciesRangeStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._connection: sqlite3.Connection | None = None

    def get_present_taxon_ids_for_cell(self, h3_cell: str) -> set[int]:
        connection = self._get_connection()

        rows = connection.execute(
            """
            SELECT taxon_id
            FROM range_cells
            WHERE h3_cell = ?
            """,
            (h3_cell,),
        ).fetchall()

        return {int(row[0]) for row in rows}

    def contains_taxon_in_cell(self, *, h3_cell: str, taxon_id: int) -> bool:
        connection = self._get_connection()

        row = connection.execute(
            """
            SELECT 1
            FROM range_cells
            WHERE h3_cell = ?
              AND taxon_id = ?
            LIMIT 1
            """,
            (h3_cell, taxon_id),
        ).fetchone()

        return row is not None

    def get_h3_resolution(self) -> int:
        connection = self._get_connection()

        row = connection.execute(
            """
            SELECT value
            FROM range_store_metadata
            WHERE key = 'h3_resolution'
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            raise ValueError("Range store metadata is missing required key: h3_resolution")

        return int(row[0])

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(
                self._database_path,
                check_same_thread=False,
            )
            self._connection.execute("PRAGMA query_only = ON")

        return self._connection
