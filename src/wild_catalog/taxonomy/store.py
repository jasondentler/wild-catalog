from collections.abc import Iterable
from typing import Protocol

from wild_catalog.taxonomy.types import CommonNameRecord, TaxonRecord


class TaxonomyStore(Protocol):
    def get_taxon(self, taxon_id: int) -> TaxonRecord | None:
        ...

    def get_common_names(self, taxon_id: int) -> tuple[CommonNameRecord, ...]:
        ...

    def iter_taxa(self) -> Iterable[TaxonRecord]:
        ...


class InMemoryTaxonomyStore:
    def __init__(
        self,
        *,
        taxa_by_id: dict[int, TaxonRecord],
        common_names_by_taxon_id: dict[int, tuple[CommonNameRecord, ...]] | None = None,
    ) -> None:
        self._taxa_by_id = dict(taxa_by_id)
        self._common_names_by_taxon_id = dict(common_names_by_taxon_id or {})

    def get_taxon(self, taxon_id: int) -> TaxonRecord | None:
        return self._taxa_by_id.get(taxon_id)

    def get_common_names(self, taxon_id: int) -> tuple[CommonNameRecord, ...]:
        return self._common_names_by_taxon_id.get(taxon_id, ())

    def iter_taxa(self) -> Iterable[TaxonRecord]:
        return self._taxa_by_id.values()
