import sqlite3
from pathlib import Path


def validate_range_store(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)

    try:
        geometry_count = connection.execute(
            "SELECT COUNT(*) FROM range_geometries"
        ).fetchone()[0]
        rtree_count = connection.execute(
            "SELECT COUNT(*) FROM range_geometries_rtree"
        ).fetchone()[0]
        metadata = dict(
            connection.execute(
                """
                SELECT key, value
                FROM range_store_metadata
                """
            ).fetchall()
        )
    finally:
        connection.close()

    if geometry_count <= 0:
        raise ValueError("Range store contains no range_geometries rows.")

    if rtree_count != geometry_count:
        raise ValueError(
            "Range store RTree row count does not match range_geometries row count."
        )

    required_metadata_keys = {
        "source",
        "source_version",
        "geometry_format",
        "built_at",
    }
    missing_metadata_keys = required_metadata_keys - set(metadata)

    if missing_metadata_keys:
        missing_keys = ", ".join(sorted(missing_metadata_keys))
        raise ValueError(f"Range store metadata is missing required keys: {missing_keys}")

    if metadata["geometry_format"] != "wkb":
        raise ValueError("Range store geometry_format must be wkb.")
