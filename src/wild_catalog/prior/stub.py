from wild_catalog.prior.store import SpeciesRangeStore


class StubSpeciesRangeStore(SpeciesRangeStore):
    def __init__(
        self,
        *,
        present_taxon_ids_by_h3_cell: dict[str, set[int]] | None = None,
        h3_resolution: int = 5,
    ) -> None:
        self._present_taxon_ids_by_h3_cell = present_taxon_ids_by_h3_cell or {}
        self._h3_resolution = h3_resolution

    def get_present_taxon_ids_for_cell(self, h3_cell: str) -> set[int]:
        return set(self._present_taxon_ids_by_h3_cell.get(h3_cell, set()))

    def contains_taxon_in_cell(self, *, h3_cell: str, taxon_id: int) -> bool:
        return taxon_id in self._present_taxon_ids_by_h3_cell.get(h3_cell, set())

    def get_h3_resolution(self) -> int:
        return self._h3_resolution
