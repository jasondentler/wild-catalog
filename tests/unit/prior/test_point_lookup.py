from shapely import to_wkb
from shapely.geometry import Polygon

from wild_catalog.prior.point_lookup import get_present_taxon_ids_at_point


def test_get_present_taxon_ids_at_point_filters_exact_geometry() -> None:
    present_taxon_ids = get_present_taxon_ids_at_point(
        latitude=0.5,
        longitude=0.5,
        candidate_geometries=[
            (101, to_wkb(_box(0.0, 0.0, 1.0, 1.0))),
            (202, to_wkb(_donut())),
        ],
    )

    assert present_taxon_ids == {101}


def test_get_present_taxon_ids_at_point_counts_boundary_as_present() -> None:
    present_taxon_ids = get_present_taxon_ids_at_point(
        latitude=0.0,
        longitude=0.5,
        candidate_geometries=[
            (101, to_wkb(_box(0.0, 0.0, 1.0, 1.0))),
        ],
    )

    assert present_taxon_ids == {101}


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


def _donut() -> Polygon:
    return Polygon(
        shell=[
            (0.0, 0.0),
            (1.0, 0.0),
            (1.0, 1.0),
            (0.0, 1.0),
            (0.0, 0.0),
        ],
        holes=[
            [
                (0.25, 0.25),
                (0.75, 0.25),
                (0.75, 0.75),
                (0.25, 0.75),
                (0.25, 0.25),
            ]
        ],
    )
