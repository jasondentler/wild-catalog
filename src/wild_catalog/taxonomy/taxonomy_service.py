from dataclasses import replace

from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.taxonomy.taxonomy_store import SQLiteTaxonomyStore


class TaxonomyService:
    def __init__(self, store: SQLiteTaxonomyStore) -> None:
        self._store = store

    def enrich_predictions(
        self,
        predictions: tuple[Prediction, ...],
        *,
        common_name_language: str = "en-US",
    ) -> tuple[Prediction, ...]:
        return tuple(
            self.enrich_prediction(
                prediction,
                common_name_language=common_name_language,
            )
            for prediction in predictions
        )

    def enrich_prediction(
        self,
        prediction: Prediction,
        *,
        common_name_language: str = "en-US",
    ) -> Prediction:
        if prediction.taxon_id < 0:
            return prediction

        accepted_taxon_id = self._store.get_accepted_taxon_id(prediction.taxon_id)
        lineage = self._store.get_lineage(accepted_taxon_id)
        if not lineage:
            return prediction

        common_names = self._store.get_common_names(
            (entry.taxon_id for entry in lineage),
            _language_preferences(common_name_language),
        )

        return replace(
            prediction,
            accepted_taxon_id=accepted_taxon_id,
            taxonomy=tuple(entry.display_name for entry in lineage),
            taxonomy_common_names=tuple(
                common_names.get(entry.taxon_id, entry.display_name)
                for entry in lineage
            ),
            taxonomy_rank_names=tuple(entry.rank for entry in lineage),
        )


def _language_preferences(common_name_language: str | None) -> tuple[str, ...]:
    normalized = (common_name_language or "en-US").strip().replace("_", "-").lower()
    preferences = []
    if normalized:
        preferences.append(normalized)
        if "-" in normalized:
            preferences.append(normalized.split("-", maxsplit=1)[0])
    preferences.append("en")

    deduplicated = []
    seen = set()
    for language in preferences:
        if language not in seen:
            seen.add(language)
            deduplicated.append(language)
    return tuple(deduplicated)
