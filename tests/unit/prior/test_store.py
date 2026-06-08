from shapely.geometry import Polygon

from tests.unit.prior.helpers import create_range_store_fixture
from wild_catalog.prior.store import SQLiteSpeciesRangeStore


def test_sqlite_store_returns_candidate_geometries_for_point(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    create_range_store_fixture(
        database_path,
        geometries=[
            (101, _box(-96.0, 29.0, -95.0, 30.0)),
            (202, _box(-96.0, 29.0, -95.0, 30.0)),
            (303, _box(-80.0, 20.0, -79.0, 21.0)),
        ],
    )

    store = SQLiteSpeciesRangeStore(database_path)

    try:
        candidates = store.get_candidate_geometries_for_point(
            latitude=29.7604,
            longitude=-95.3698,
        )
        missing = store.get_candidate_geometries_for_point(
            latitude=10.0,
            longitude=10.0,
        )
    finally:
        store.close()

    assert [taxon_id for taxon_id, _ in candidates] == [101, 202]
    assert missing == []


def test_sqlite_store_filters_candidate_geometries_by_taxa(tmp_path) -> None:
    database_path = tmp_path / "ranges.sqlite3"

    create_range_store_fixture(
        database_path,
        geometries=[
            (101, _box(-96.0, 29.0, -95.0, 30.0)),
            (202, _box(-96.0, 29.0, -95.0, 30.0)),
            (303, _box(-96.0, 29.0, -95.0, 30.0)),
        ],
    )

    store = SQLiteSpeciesRangeStore(database_path)

    try:
        candidates = store.get_candidate_geometries_for_taxa_at_point(
            latitude=29.7604,
            longitude=-95.3698,
            taxon_ids={101, 303},
        )
    finally:
        store.close()

    assert [taxon_id for taxon_id, _ in candidates] == [101, 303]


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
