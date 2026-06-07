from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TaxonRecord:
    taxon_id: int
    parent_taxon_id: int | None
    rank: str
    scientific_name: str
    accepted_taxon_id: int | None = None


@dataclass(frozen=True, slots=True)
class EnrichedPrediction:
    confidence: float
    is_present: bool
    taxonomy: tuple[str, ...]
    taxonomy_common_names: tuple[str, ...]
