from __future__ import annotations

import re
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


@dataclass(frozen=True, slots=True)
class TaxonomySearchMatch:
    taxon_id: int
    matched_name: str
    score: int


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

    def get_taxon_ids_with_present_descendants(
        self,
        taxon_ids: Iterable[int],
        present_taxon_ids: Iterable[int],
    ) -> set[int]:
        requested_taxon_ids = sorted(set(taxon_ids))
        requested_present_taxon_ids = sorted(set(present_taxon_ids))
        if not requested_taxon_ids or not requested_present_taxon_ids:
            return set()

        present_placeholders = ", ".join("?" for _ in requested_present_taxon_ids)
        requested_placeholders = ", ".join("?" for _ in requested_taxon_ids)
        rows = self._get_connection().execute(
            f"""
            WITH RECURSIVE present_lineage AS (
                SELECT taxon_id, parent_taxon_id
                FROM taxonomy_taxa
                WHERE taxon_id IN ({present_placeholders})

                UNION

                SELECT parent.taxon_id, parent.parent_taxon_id
                FROM taxonomy_taxa parent
                JOIN present_lineage child
                  ON parent.taxon_id = child.parent_taxon_id
            )
            SELECT DISTINCT taxon_id
            FROM present_lineage
            WHERE taxon_id IN ({requested_placeholders})
            """,
            (*requested_present_taxon_ids, *requested_taxon_ids),
        ).fetchall()

        return {int(row[0]) for row in rows}

    def search_scientific_names(
        self,
        query: str,
        *,
        limit: int,
    ) -> tuple[TaxonomySearchMatch, ...]:
        fts_query = _to_prefix_fts_query(query)
        if not fts_query:
            return ()

        rows = self._get_connection().execute(
            """
            SELECT taxon_id, matched_name, score
            FROM (
                SELECT
                    taxon_id,
                    scientific_name AS matched_name,
                    CASE
                        WHEN lower(scientific_name) = lower(?) THEN 0
                        WHEN lower(scientific_name) = lower(display_name) THEN 1
                        WHEN substr(lower(scientific_name), 1, length(?)) = lower(?) THEN 2
                        ELSE 3
                    END AS score
                FROM taxonomy_taxa_fts
                WHERE scientific_name MATCH ?

                UNION ALL

                SELECT
                    taxon_id,
                    display_name AS matched_name,
                    CASE
                        WHEN lower(display_name) = lower(?) THEN 0
                        WHEN substr(lower(display_name), 1, length(?)) = lower(?) THEN 2
                        ELSE 3
                    END AS score
                FROM taxonomy_taxa_fts
                WHERE display_name != scientific_name
                  AND display_name MATCH ?
            )
            ORDER BY score, lower(matched_name), taxon_id
            LIMIT ?
            """,
            (
                query,
                query,
                query,
                fts_query,
                query,
                query,
                query,
                fts_query,
                limit,
            ),
        ).fetchall()

        return _search_matches_from_rows(rows)

    def search_common_names(
        self,
        query: str,
        *,
        language_preferences: Sequence[str],
        limit: int,
    ) -> tuple[TaxonomySearchMatch, ...]:
        fts_query = _to_prefix_fts_query(query)
        requested_languages = tuple(dict.fromkeys(language_preferences))
        if not fts_query or not requested_languages:
            return ()

        language_values = {
            language: index for index, language in enumerate(requested_languages)
        }
        language_case = " ".join(
            f"WHEN ? THEN {index}" for index, _language in enumerate(requested_languages)
        )

        rows = self._get_connection().execute(
            f"""
            SELECT taxon_id, vernacular_name, score
            FROM (
                SELECT
                    taxon_id,
                    vernacular_name,
                    CASE
                        WHEN lower(vernacular_name) = lower(?) THEN 0
                        WHEN substr(lower(vernacular_name), 1, length(?)) = lower(?) THEN 2
                        ELSE 3
                    END AS name_score,
                    CASE language_code {language_case} ELSE 1000 END AS language_score,
                    (
                        CASE
                            WHEN lower(vernacular_name) = lower(?) THEN 0
                            WHEN substr(lower(vernacular_name), 1, length(?)) = lower(?) THEN 2
                            ELSE 3
                        END * 100
                    ) + CASE language_code {language_case} ELSE 1000 END AS score
                FROM taxonomy_vernacular_names_fts
                WHERE vernacular_name MATCH ?
                  AND language_code IN ({", ".join("?" for _ in requested_languages)})
            )
            ORDER BY name_score, language_score, lower(vernacular_name), taxon_id
            LIMIT ?
            """,
            (
                query,
                query,
                query,
                *language_values.keys(),
                query,
                query,
                query,
                *language_values.keys(),
                fts_query,
                *requested_languages,
                limit,
            ),
        ).fetchall()

        return _search_matches_from_rows(rows)

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


def _to_prefix_fts_query(query: str) -> str:
    terms = re.findall(r"\w+", query.lower())
    return " ".join(f"{term}*" for term in terms)


def _search_matches_from_rows(rows: Iterable[sqlite3.Row | tuple[object, ...]]):
    return tuple(
        TaxonomySearchMatch(
            taxon_id=int(row[0]),
            matched_name=str(row[1]),
            score=int(row[2]),
        )
        for row in rows
    )
