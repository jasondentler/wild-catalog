import sqlite3

import pytest
from shapely.geometry import Polygon

from wild_catalog.prior.build.sqlite_writer import create_range_store
from wild_catalog.prior.build.validate import validate_range_store


def test_validate_range_store_accepts_valid_store(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    create_range_store(
        database_path,
        geometries=[(101, _box(-96.0, 29.0, -95.0, 30.0))],
        source="test",
        source_version="test",
    )

    validate_range_store(database_path)


def test_validate_range_store_rejects_empty_range_geometries(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    create_range_store(
        database_path,
        geometries=[],
        source="test",
        source_version="test",
    )

    with pytest.raises(ValueError, match="no range_geometries rows"):
        validate_range_store(database_path)


def test_validate_range_store_rejects_rtree_count_mismatch(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    create_range_store(
        database_path,
        geometries=[(101, _box(-96.0, 29.0, -95.0, 30.0))],
        source="test",
        source_version="test",
    )

    connection = sqlite3.connect(database_path)

    try:
        connection.execute("DELETE FROM range_geometries_rtree")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="RTree row count"):
        validate_range_store(database_path)


def test_validate_range_store_rejects_missing_metadata(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    create_range_store(
        database_path,
        geometries=[(101, _box(-96.0, 29.0, -95.0, 30.0))],
        source="test",
        source_version="test",
    )

    connection = sqlite3.connect(database_path)

    try:
        connection.execute(
            """
            DELETE FROM range_store_metadata
            WHERE key = 'geometry_format'
            """
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="geometry_format"):
        validate_range_store(database_path)


def _box(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Polygon:
    return Polygon(
        [
            (min_lon, min_lat),
            (max_lon, min_lat),
            (max_lon, max_lat),
            (min_lon, max_lat),
            (min_lon, min_lat),
        ]
    )
