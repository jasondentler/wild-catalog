from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaxonRecord:
    taxon_id: int
    scientific_name: str
    rank: str
    parent_taxon_id: int | None
    accepted_taxon_id: int | None = None
    is_active: bool = True


@dataclass(frozen=True, slots=True)
class CommonNameRecord:
    taxon_id: int
    locale: str
    name: str


@dataclass(frozen=True, slots=True)
class TaxonLineage:
    taxon_ids: tuple[int, ...]
    scientific_names: tuple[str, ...]
    ranks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class EnrichedPrediction:
    confidence: float = 0.0
    is_present: bool = False
    taxonomy: tuple[str, ...] = ()
    taxonomy_common_names: tuple[str, ...] = ()
    class_id: int = -1
    taxon_id: int = -1
    accepted_taxon_id: int = -1
    taxonomy_rank_names: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TaxonomySnapshot:
    taxa_by_id: Mapping[int, TaxonRecord]
    common_names_by_taxon_id: Mapping[int, tuple[CommonNameRecord, ...]]
