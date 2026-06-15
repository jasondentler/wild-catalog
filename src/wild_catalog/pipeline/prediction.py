from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Prediction:
    confidence: float = 0.0
    is_present: bool = False
    taxonomy: tuple[str, ...] = ()
    taxonomy_common_names: tuple[str, ...] = ()
    class_id: int = -1
    taxon_id: int = -1
    accepted_taxon_id: int = -1
    taxonomy_rank_names: tuple[str, ...] = ()
