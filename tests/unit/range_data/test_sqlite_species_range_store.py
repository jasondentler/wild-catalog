import sqlite3
from contextlib import closing

from wild_catalog.range_data.inaturalist_open_range_importer import (
    create_range_store_schema,
)
from wild_catalog.range_data.sqlite_species_range_store import SQLiteSpeciesRangeStore


def test_sqlite_species_range_store_finds_candidates_for_point(tmp_path) -> None:
    database_path = tmp_path / "range-store.sqlite"
    _create_range_store(database_path)
    store = SQLiteSpeciesRangeStore(database_path)

    candidates = store.get_candidate_geometries_for_point(
        latitude=29.5,
        longitude=-94.5,
    )

    assert candidates == [(10, b"first-wkb")]
    store.close()


def test_sqlite_species_range_store_filters_candidates_by_taxa(tmp_path) -> None:
    database_path = tmp_path / "range-store.sqlite"
    _create_range_store(database_path)
    store = SQLiteSpeciesRangeStore(database_path)

    candidates = store.get_candidate_geometries_for_taxa_at_point(
        latitude=29.5,
        longitude=-94.5,
        taxon_ids=[20, 10],
    )

    assert candidates == [(10, b"first-wkb")]
    store.close()


def test_sqlite_species_range_store_returns_empty_list_without_taxa(tmp_path) -> None:
    database_path = tmp_path / "range-store.sqlite"
    _create_range_store(database_path)
    store = SQLiteSpeciesRangeStore(database_path)

    assert (
        store.get_candidate_geometries_for_taxa_at_point(
            latitude=29.5,
            longitude=-94.5,
            taxon_ids=[],
        )
        == []
    )
    store.close()


def test_sqlite_species_range_store_close_is_idempotent(tmp_path) -> None:
    database_path = tmp_path / "range-store.sqlite"
    _create_range_store(database_path)
    store = SQLiteSpeciesRangeStore(database_path)

    store.close()
    store.close()


def _create_range_store(database_path) -> None:
    with closing(sqlite3.connect(database_path)) as connection:
        with connection:
            create_range_store_schema(connection)
            connection.execute(
                """
                INSERT INTO range_geometries (
                    id,
                    taxon_id,
                    min_lon,
                    min_lat,
                    max_lon,
                    max_lat,
                    geometry_wkb
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (1, 10, -95.0, 29.0, -94.0, 30.0, b"first-wkb"),
            )
            connection.execute(
                """
                INSERT INTO range_geometries (
                    id,
                    taxon_id,
                    min_lon,
                    min_lat,
                    max_lon,
                    max_lat,
                    geometry_wkb
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (2, 20, -80.0, 40.0, -79.0, 41.0, b"second-wkb"),
            )
            connection.executemany(
                """
                INSERT INTO range_geometries_rtree (id, min_lon, max_lon, min_lat, max_lat)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (1, -95.0, -94.0, 29.0, 30.0),
                    (2, -80.0, -79.0, 40.0, 41.0),
                ],
            )
