from collections.abc import Iterable, Mapping

from wild_catalog.range_data.species_range_store import SpeciesRangeStore


class StubSpeciesRangeStore(SpeciesRangeStore):
    def __init__(
        self,
        *,
        candidate_geometries: Iterable[tuple[int, bytes]] | None = None,
        taxon_id_by_name: Mapping[str, int] | None = None,
    ) -> None:
        self._candidate_geometries = list(candidate_geometries or [])
        self._taxon_id_by_name = dict(taxon_id_by_name or {})

    def get_candidate_geometries_for_point(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> list[tuple[int, bytes]]:
        return list(self._candidate_geometries)

    def get_candidate_geometries_for_taxa_at_point(
        self,
        *,
        latitude: float,
        longitude: float,
        taxon_ids: Iterable[int],
    ) -> list[tuple[int, bytes]]:
        requested_taxon_ids = set(taxon_ids)
        return [
            (taxon_id, geometry_wkb)
            for taxon_id, geometry_wkb in self._candidate_geometries
            if taxon_id in requested_taxon_ids
        ]

    def get_taxon_ids_by_names(
        self,
        scientific_names: Iterable[str],
    ) -> Mapping[str, int]:
        requested_names = set(scientific_names)
        return {
            name: taxon_id
            for name, taxon_id in self._taxon_id_by_name.items()
            if name in requested_names
        }
