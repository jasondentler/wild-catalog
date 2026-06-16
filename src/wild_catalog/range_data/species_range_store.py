from collections.abc import Iterable
from typing import Protocol


class SpeciesRangeStore(Protocol):
    def get_candidate_geometries_for_point(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> list[tuple[int, bytes]]:
        ...

    def get_candidate_geometries_for_taxa_at_point(
        self,
        *,
        latitude: float,
        longitude: float,
        taxon_ids: Iterable[int],
    ) -> list[tuple[int, bytes]]:
        ...
