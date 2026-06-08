import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from math import isfinite
from pathlib import Path
from typing import Any

from shapely import to_wkb

SCHEMA_SQL = """
CREATE TABLE range_geometries (
    id INTEGER PRIMARY KEY,
    taxon_id INTEGER NOT NULL,
    min_lon REAL NOT NULL,
    min_lat REAL NOT NULL,
    max_lon REAL NOT NULL,
    max_lat REAL NOT NULL,
    geometry_wkb BLOB NOT NULL
);

CREATE VIRTUAL TABLE range_geometries_rtree USING rtree(
    id,
    min_lon,
    max_lon,
    min_lat,
    max_lat
);

CREATE INDEX idx_range_geometries_taxon_id
ON range_geometries (taxon_id);

CREATE TABLE range_store_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def create_range_store(
    database_path: Path,
    *,
    geometries: Iterable[tuple[int, Any]],
    source: str,
    source_version: str,
    batch_size: int = 2_000,
) -> int:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive.")

    database_path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = database_path.with_suffix(database_path.suffix + ".tmp")

    if temporary_path.exists():
        temporary_path.unlink()

    connection = sqlite3.connect(temporary_path)

    try:
        connection.executescript(SCHEMA_SQL)
        attempted_geometry_count = 0
        inserted_geometry_count = 0

        for taxon_id, geometry in geometries:
            attempted_geometry_count += 1

            if geometry is None or geometry.is_empty:
                continue

            min_lon, min_lat, max_lon, max_lat = geometry.bounds

            if not all(isfinite(value) for value in (min_lon, min_lat, max_lon, max_lat)):
                continue

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

            if geometry_id is None:
                raise RuntimeError("SQLite did not return a geometry row id.")

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
            inserted_geometry_count += 1

            if inserted_geometry_count % batch_size == 0:
                connection.commit()

        if inserted_geometry_count % batch_size != 0:
            connection.commit()

        metadata = {
            "source": source,
            "source_version": source_version,
            "geometry_format": "wkb",
            "built_at": datetime.now(UTC).isoformat(),
            "attempted_geometry_rows": str(attempted_geometry_count),
            "inserted_geometry_rows": str(inserted_geometry_count),
        }

        connection.executemany(
            """
            INSERT INTO range_store_metadata (key, value)
            VALUES (?, ?)
            """,
            metadata.items(),
        )
        connection.commit()
        connection.execute("VACUUM")
        connection.close()

        temporary_path.replace(database_path)
        return inserted_geometry_count
    except Exception:
        connection.close()
        if temporary_path.exists():
            temporary_path.unlink()
        raise
