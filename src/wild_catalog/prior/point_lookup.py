from collections.abc import Iterable

from shapely import Point, from_wkb


def get_present_taxon_ids_at_point(
    *,
    latitude: float,
    longitude: float,
    candidate_geometries: Iterable[tuple[int, bytes]],
) -> set[int]:
    point = Point(longitude, latitude)
    present_taxon_ids: set[int] = set()

    for taxon_id, geometry_wkb in candidate_geometries:
        geometry = from_wkb(geometry_wkb)

        if geometry.covers(point):
            present_taxon_ids.add(taxon_id)

    return present_taxon_ids
