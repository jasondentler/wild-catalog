import sqlite3

from shapely.geometry import Polygon

from wild_catalog.prior.build.sqlite_writer import create_range_store


def test_create_range_store_writes_schema_geometries_rtree_and_metadata(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    inserted_geometry_count = create_range_store(
        database_path,
        geometries=[
            (101, _box(-96.0, 29.0, -95.0, 30.0)),
            (202, _box(-80.0, 20.0, -79.0, 21.0)),
        ],
        source="test-source",
        source_version="test-version",
    )

    connection = sqlite3.connect(database_path)

    try:
        rows = connection.execute(
            """
            SELECT taxon_id, min_lon, min_lat, max_lon, max_lat
            FROM range_geometries
            ORDER BY taxon_id
            """
        ).fetchall()
        rtree_rows = connection.execute(
            """
            SELECT min_lon, max_lon, min_lat, max_lat
            FROM range_geometries_rtree
            ORDER BY id
            """
        ).fetchall()
        indexes = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'index'
              AND name = 'idx_range_geometries_taxon_id'
            """
        ).fetchall()
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

    assert rows == [
        (101, -96.0, 29.0, -95.0, 30.0),
        (202, -80.0, 20.0, -79.0, 21.0),
    ]
    assert rtree_rows == [
        (-96.0, -95.0, 29.0, 30.0),
        (-80.0, -79.0, 20.0, 21.0),
    ]
    assert inserted_geometry_count == 2
    assert indexes == [("idx_range_geometries_taxon_id",)]
    assert metadata["source"] == "test-source"
    assert metadata["source_version"] == "test-version"
    assert metadata["geometry_format"] == "wkb"
    assert metadata["attempted_geometry_rows"] == "2"
    assert metadata["inserted_geometry_rows"] == "2"
    assert "built_at" in metadata


def test_create_range_store_skips_empty_geometries(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    inserted_geometry_count = create_range_store(
        database_path,
        geometries=[
            (101, Polygon()),
            (202, _box(-80.0, 20.0, -79.0, 21.0)),
        ],
        source="test-source",
        source_version="test-version",
    )

    connection = sqlite3.connect(database_path)

    try:
        row_count = connection.execute("SELECT COUNT(*) FROM range_geometries").fetchone()[0]
    finally:
        connection.close()

    assert inserted_geometry_count == 1
    assert row_count == 1


def test_create_range_store_rejects_invalid_batch_size(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    try:
        create_range_store(
            database_path,
            geometries=[],
            source="test-source",
            source_version="test-version",
            batch_size=0,
        )
    except ValueError as exc:
        assert "batch_size" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


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
