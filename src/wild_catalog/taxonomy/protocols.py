from collections.abc import Mapping, Sequence
from typing import Protocol

from wild_catalog.classifier.types import ClassIndex, ClassPrediction
from wild_catalog.taxonomy.types import EnrichedPrediction


class TaxonomyServiceProtocol(Protocol):
    def enrich_predictions(
        self,
        predictions: Sequence[ClassPrediction],
        class_index: ClassIndex,
        common_name_language: str,
        presence_by_taxon_id: Mapping[int, bool],
    ) -> list[EnrichedPrediction]:
        ...
