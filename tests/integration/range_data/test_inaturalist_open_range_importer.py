import os
import sqlite3
from contextlib import closing

import pytest

from wild_catalog.range_data import import_geopackages

pytestmark = pytest.mark.integration

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)


@requires_enabled_integration_suite
def test_import_geopackages_imports_split_archive_files_into_range_store(tmp_path) -> None:
    target_database_path = tmp_path / "inaturalist-range-store.sqlite"
    first_archive = tmp_path / "iNaturalist_geomodel_Aves_1.gpkg"
    second_archive = tmp_path / "iNaturalist_geomodel_Aves_2.gpkg"
    _create_fake_geopackage(
        first_archive,
        table_name="iNaturalist_geomodel_Aves",
        rows=[
            {
                "fid": 1,
                "taxon_id": "111",
                "wkb": b"first-bird-range",
                "bounds": (-100.0, -99.0, 30.0, 31.0),
            }
        ],
    )
    _create_fake_geopackage(
        second_archive,
        table_name="iNaturalist_geomodel_Aves",
        rows=[
            {
                "fid": 1,
                "taxon_id": "222",
                "wkb": b"second-bird-range",
                "bounds": (-97.0, -96.0, 32.0, 33.0),
            }
        ],
    )

    rows_imported = import_geopackages(
        target_database_path,
        [first_archive, second_archive],
        metadata={"version": "2.31", "ranges": 2, "collections": {"Aves": {"archives": 2}}},
    )

    assert rows_imported == 2
    with closing(sqlite3.connect(target_database_path)) as connection:
        range_rows = connection.execute(
            """
            SELECT id, taxon_id, min_lon, min_lat, max_lon, max_lat, geometry_wkb
            FROM range_geometries
            ORDER BY id
            """
        ).fetchall()
        rtree_rows = connection.execute(
            """
            SELECT id, min_lon, max_lon, min_lat, max_lat
            FROM range_geometries_rtree
            ORDER BY id
            """
        ).fetchall()
        metadata_rows = dict(
            connection.execute(
                "SELECT key, value FROM range_store_metadata ORDER BY key"
            ).fetchall()
        )

    assert range_rows == [
        (1, 111, -100.0, 30.0, -99.0, 31.0, b"first-bird-range"),
        (2, 222, -97.0, 32.0, -96.0, 33.0, b"second-bird-range"),
    ]
    assert rtree_rows == [
        (1, -100.0, -99.0, 30.0, 31.0),
        (2, -97.0, -96.0, 32.0, 33.0),
    ]
    assert metadata_rows == {"ranges": "2", "version": "2.31"}


def _create_fake_geopackage(geopackage_path, table_name: str, rows: list[dict]) -> None:
    with closing(sqlite3.connect(geopackage_path)) as connection:
        with connection:
            connection.execute(
                f"""
                CREATE TABLE "{table_name}" (
                    fid INTEGER PRIMARY KEY,
                    taxon_id TEXT NOT NULL,
                    geom BLOB NOT NULL
                )
                """
            )
            connection.execute(
                f"""
                CREATE TABLE "rtree_{table_name}_geom" (
                    id INTEGER PRIMARY KEY,
                    minx REAL NOT NULL,
                    maxx REAL NOT NULL,
                    miny REAL NOT NULL,
                    maxy REAL NOT NULL
                )
                """
            )
            for row in rows:
                minx, maxx, miny, maxy = row["bounds"]
                geometry_with_header = b"abcAefgh" + row["wkb"]
                connection.execute(
                    f'INSERT INTO "{table_name}" (fid, taxon_id, geom) VALUES (?, ?, ?)',
                    (row["fid"], row["taxon_id"], geometry_with_header),
                )
                connection.execute(
                    f'INSERT INTO "rtree_{table_name}_geom" (id, minx, maxx, miny, maxy) '
                    "VALUES (?, ?, ?, ?, ?)",
                    (row["fid"], minx, maxx, miny, maxy),
                )
