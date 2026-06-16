import sqlite3
from collections.abc import Iterable
from pathlib import Path

from wild_catalog.range_data.species_range_store import SpeciesRangeStore


class SQLiteSpeciesRangeStore(SpeciesRangeStore):
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._connection: sqlite3.Connection | None = None

    def get_candidate_geometries_for_point(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> list[tuple[int, bytes]]:
        connection = self._get_connection()

        rows = connection.execute(
            """
            SELECT range_geometries.taxon_id, range_geometries.geometry_wkb
            FROM range_geometries_rtree
            JOIN range_geometries
              ON range_geometries.id = range_geometries_rtree.id
            WHERE range_geometries_rtree.min_lon <= ?
              AND range_geometries_rtree.max_lon >= ?
              AND range_geometries_rtree.min_lat <= ?
              AND range_geometries_rtree.max_lat >= ?
            """,
            (longitude, longitude, latitude, latitude),
        ).fetchall()

        return [(int(row[0]), bytes(row[1])) for row in rows]

    def get_candidate_geometries_for_taxa_at_point(
        self,
        *,
        latitude: float,
        longitude: float,
        taxon_ids: Iterable[int],
    ) -> list[tuple[int, bytes]]:
        requested_taxon_ids = sorted(set(taxon_ids))

        if not requested_taxon_ids:
            return []

        connection = self._get_connection()
        placeholders = ", ".join("?" for _ in requested_taxon_ids)

        rows = connection.execute(
            f"""
            SELECT range_geometries.taxon_id, range_geometries.geometry_wkb
            FROM range_geometries_rtree
            JOIN range_geometries
              ON range_geometries.id = range_geometries_rtree.id
            WHERE range_geometries_rtree.min_lon <= ?
              AND range_geometries_rtree.max_lon >= ?
              AND range_geometries_rtree.min_lat <= ?
              AND range_geometries_rtree.max_lat >= ?
              AND range_geometries.taxon_id IN ({placeholders})
            """,
            (longitude, longitude, latitude, latitude, *requested_taxon_ids),
        ).fetchall()

        return [(int(row[0]), bytes(row[1])) for row in rows]

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
