import sqlite3
from pathlib import Path
from typing import Any

from shapely import to_wkb


def create_range_store_fixture(
    database_path: Path,
    *,
    geometries: list[tuple[int, Any]],
) -> None:
    connection = sqlite3.connect(database_path)

    try:
        connection.execute(
            """
            CREATE TABLE range_geometries (
                id INTEGER PRIMARY KEY,
                taxon_id INTEGER NOT NULL,
                min_lon REAL NOT NULL,
                min_lat REAL NOT NULL,
                max_lon REAL NOT NULL,
                max_lat REAL NOT NULL,
                geometry_wkb BLOB NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE VIRTUAL TABLE range_geometries_rtree USING rtree(
                id,
                min_lon,
                max_lon,
                min_lat,
                max_lat
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX idx_range_geometries_taxon_id
            ON range_geometries (taxon_id)
            """
        )
        connection.execute(
            """
            CREATE TABLE range_store_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO range_store_metadata (key, value)
            VALUES ('geometry_format', 'wkb')
            """,
        )

        for taxon_id, geometry in geometries:
            min_lon, min_lat, max_lon, max_lat = geometry.bounds
            cursor = connection.execute(
                """
                INSERT INTO range_geometries (
                    taxon_id,
                    min_lon,
                    min_lat,
                    max_lon,
                    max_lat,
                    geometry_wkb
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    taxon_id,
                    min_lon,
                    min_lat,
                    max_lon,
                    max_lat,
                    sqlite3.Binary(to_wkb(geometry)),
                ),
            )
            geometry_id = cursor.lastrowid
            connection.execute(
                """
                INSERT INTO range_geometries_rtree (
                    id,
                    min_lon,
                    max_lon,
                    min_lat,
                    max_lat
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (geometry_id, min_lon, max_lon, min_lat, max_lat),
            )

        connection.commit()
    finally:
        connection.close()
