from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TaxonLineageEntry:
    taxon_id: int
    rank: str
    scientific_name: str
    display_name: str


class SQLiteTaxonomyStore:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._connection: sqlite3.Connection | None = None

    def get_accepted_taxon_id(self, taxon_id: int) -> int:
        row = self._get_connection().execute(
            """
            SELECT accepted_taxon_id
            FROM taxonomy_taxa
            WHERE taxon_id = ?
            """,
            (taxon_id,),
        ).fetchone()
        if row is None or row[0] is None:
            return taxon_id
        return int(row[0])

    def get_lineage(self, taxon_id: int) -> tuple[TaxonLineageEntry, ...]:
        connection = self._get_connection()
        rows = connection.execute(
            """
            WITH RECURSIVE lineage AS (
                SELECT
                    taxon_id,
                    parent_taxon_id,
                    rank,
                    scientific_name,
                    display_name,
                    0 AS depth
                FROM taxonomy_taxa
                WHERE taxon_id = ?

                UNION ALL

                SELECT
                    parent.taxon_id,
                    parent.parent_taxon_id,
                    parent.rank,
                    parent.scientific_name,
                    parent.display_name,
                    lineage.depth + 1
                FROM taxonomy_taxa parent
                JOIN lineage ON parent.taxon_id = lineage.parent_taxon_id
            )
            SELECT taxon_id, rank, scientific_name, display_name
            FROM lineage
            WHERE rank != 'stateofmatter'
            ORDER BY depth DESC
            """,
            (taxon_id,),
        ).fetchall()

        return tuple(
            TaxonLineageEntry(
                taxon_id=int(row[0]),
                rank=str(row[1]),
                scientific_name=str(row[2]),
                display_name=str(row[3]),
            )
            for row in rows
        )

    def get_common_names(
        self,
        taxon_ids: Iterable[int],
        language_preferences: Sequence[str],
    ) -> dict[int, str]:
        requested_taxon_ids = sorted(set(taxon_ids))
        if not requested_taxon_ids or not language_preferences:
            return {}

        placeholders = ", ".join("?" for _ in requested_taxon_ids)
        language_values = {language: index for index, language in enumerate(language_preferences)}
        language_case = " ".join(
            f"WHEN ? THEN {index}" for index, _language in enumerate(language_preferences)
        )

        rows = self._get_connection().execute(
            f"""
            SELECT taxon_id, vernacular_name
            FROM (
                SELECT
                    taxon_id,
                    vernacular_name,
                    ROW_NUMBER() OVER (
                        PARTITION BY taxon_id
                        ORDER BY
                            CASE language_code {language_case} ELSE 1000 END,
                            position
                    ) AS row_number
                FROM taxonomy_vernacular_names
                WHERE taxon_id IN ({placeholders})
                  AND language_code IN ({", ".join("?" for _ in language_preferences)})
            )
            WHERE row_number = 1
            """,
            (
                *language_values.keys(),
                *requested_taxon_ids,
                *language_preferences,
            ),
        ).fetchall()

        return {int(row[0]): str(row[1]) for row in rows}

    def get_taxon_ids_by_scientific_names(
        self,
        scientific_names: Iterable[str],
    ) -> dict[str, int]:
        requested_names = sorted({name for name in scientific_names if name})
        if not requested_names:
            return {}

        placeholders = ", ".join("?" for _ in requested_names)
        rows = self._get_connection().execute(
            f"""
            SELECT scientific_name, taxon_id
            FROM taxonomy_taxa
            WHERE scientific_name IN ({placeholders})
            """,
            requested_names,
        ).fetchall()
        return {str(row[0]): int(row[1]) for row in rows}

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> SQLiteTaxonomyStore:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _get_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = sqlite3.connect(
                self._database_path,
                check_same_thread=False,
            )
            self._connection.execute("PRAGMA query_only = ON")

        return self._connection
