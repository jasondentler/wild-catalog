from collections.abc import Iterable, Mapping
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

    def get_taxon_ids_by_names(
        self,
        scientific_names: Iterable[str],
    ) -> Mapping[str, int]:
        ...
