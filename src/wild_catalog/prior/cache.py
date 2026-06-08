from collections import OrderedDict

from wild_catalog.core.types import GpsCoordinates
from wild_catalog.prior.h3_index import gps_coordinates_to_h3_cell


def presence_cache_key(
    gps_coordinates: GpsCoordinates,
    *,
    h3_resolution: int,
) -> str:
    return gps_coordinates_to_h3_cell(
        gps_coordinates,
        resolution=h3_resolution,
    )


class PresenceCache:
    def __init__(self, *, max_entries: int) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive.")

        self._max_entries = max_entries
        self._present_taxon_ids_by_key: OrderedDict[str, set[int]] = OrderedDict()

    def get(self, key: str) -> set[int] | None:
        present_taxon_ids = self._present_taxon_ids_by_key.get(key)

        if present_taxon_ids is None:
            return None

        self._present_taxon_ids_by_key.move_to_end(key)
        return set(present_taxon_ids)

    def put(self, key: str, present_taxon_ids: set[int]) -> None:
        self._present_taxon_ids_by_key[key] = set(present_taxon_ids)
        self._present_taxon_ids_by_key.move_to_end(key)

        while len(self._present_taxon_ids_by_key) > self._max_entries:
            self._present_taxon_ids_by_key.popitem(last=False)
