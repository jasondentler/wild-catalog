from dataclasses import dataclass, replace
from typing import Literal

from wild_catalog.core.taxonomy_name_normalization import (
    capitalize_words,
    normalize_scientific_names,
)
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.range_data.species_range_prior_service import SpeciesRangePriorService
from wild_catalog.taxonomy.taxonomy_store import SQLiteTaxonomyStore, TaxonLineageEntry

SEARCH_RESULT_LIMIT = 20
SEARCH_CANDIDATE_LIMIT = 100
SearchField = Literal["common", "scientific"]


@dataclass(frozen=True, slots=True)
class TaxonomySearchResult:
    taxonomy: tuple[str, ...]
    taxonomy_rank_names: tuple[str, ...]
    taxonomy_common_names: tuple[str, ...]


class TaxonomyService:
    def __init__(
        self,
        store: SQLiteTaxonomyStore,
        *,
        range_prior_service: SpeciesRangePriorService | None = None,
    ) -> None:
        self._store = store
        self._range_prior_service = range_prior_service

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
            return _pad_unknown_taxon_prediction(prediction)

        accepted_taxon_id = self._store.get_accepted_taxon_id(prediction.taxon_id)
        lineage = self._store.get_lineage(accepted_taxon_id)
        if not lineage:
            return _pad_unknown_taxon_prediction(prediction)

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

    def search(
        self,
        query: str,
        *,
        field: SearchField | None = None,
        language_preferences: tuple[str, ...] = ("en-US",),
        gps_coordinates: GpsCoordinates | None = None,
    ) -> tuple[TaxonomySearchResult, ...]:
        normalized_query = query.strip()
        if not normalized_query:
            return ()

        resolved_language_preferences = _language_preferences_for_tags(
            language_preferences
        )
        search_language_preferences = _search_language_preferences_for_tags(
            language_preferences
        )
        matches = []

        if field in {None, "scientific"}:
            matches.extend(
                self._store.search_scientific_names(
                    normalized_query,
                    limit=SEARCH_CANDIDATE_LIMIT,
                )
            )

        if field in {None, "common"}:
            matches.extend(
                self._store.search_common_names(
                    normalized_query,
                    language_preferences=search_language_preferences,
                    limit=SEARCH_CANDIDATE_LIMIT,
                )
            )

        ranked_matches = sorted(
            matches,
            key=lambda item: (item.score, item.matched_name.lower(), item.taxon_id),
        )
        ranked_accepted_taxon_ids = []
        seen_accepted_taxon_ids = set()
        for match in ranked_matches:
            accepted_taxon_id = self._store.get_accepted_taxon_id(match.taxon_id)
            if accepted_taxon_id in seen_accepted_taxon_ids:
                continue

            seen_accepted_taxon_ids.add(accepted_taxon_id)
            ranked_accepted_taxon_ids.append(accepted_taxon_id)

        allowed_taxon_ids = self._gps_filtered_taxon_ids(
            ranked_accepted_taxon_ids,
            gps_coordinates,
        )

        results = []
        for accepted_taxon_id in ranked_accepted_taxon_ids:
            if allowed_taxon_ids is not None and accepted_taxon_id not in allowed_taxon_ids:
                continue

            lineage = self._store.get_lineage(accepted_taxon_id)
            if not lineage:
                continue

            results.append(
                self._search_result_from_lineage(
                    lineage,
                    language_preferences=resolved_language_preferences,
                )
            )

            if len(results) == SEARCH_RESULT_LIMIT:
                break

        return tuple(results)

    def _gps_filtered_taxon_ids(
        self,
        candidate_taxon_ids: tuple[int, ...] | list[int],
        gps_coordinates: GpsCoordinates | None,
    ) -> set[int] | None:
        if gps_coordinates is None or self._range_prior_service is None:
            return None

        present_taxon_ids = self._range_prior_service.get_present_taxon_ids(
            gps_coordinates
        )
        return self._store.get_taxon_ids_with_present_descendants(
            candidate_taxon_ids,
            present_taxon_ids,
        )

    def close(self) -> None:
        self._store.close()

    def __enter__(self) -> "TaxonomyService":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def _search_result_from_lineage(
        self,
        lineage: tuple[TaxonLineageEntry, ...],
        *,
        language_preferences: tuple[str, ...],
    ) -> TaxonomySearchResult:
        common_names = self._store.get_common_names(
            (entry.taxon_id for entry in lineage),
            language_preferences,
        )

        taxonomy = tuple(entry.display_name for entry in lineage)
        taxonomy_rank_names = tuple(entry.rank for entry in lineage)
        taxonomy_common_names = tuple(
            capitalize_words(
                common_names.get(entry.taxon_id, entry.display_name)
            )
            for entry in lineage
        )

        return TaxonomySearchResult(
            taxonomy=normalize_scientific_names(taxonomy, taxonomy_rank_names),
            taxonomy_common_names=taxonomy_common_names,
            taxonomy_rank_names=taxonomy_rank_names,
        )


def _language_preferences(common_name_language: str | None) -> tuple[str, ...]:
    return _language_preferences_for_tags((common_name_language or "en-US",))


def _language_preferences_for_tags(language_tags: tuple[str, ...]) -> tuple[str, ...]:
    return _deduplicate_languages(
        (*_language_tag_preferences(language_tags), "en")
    )


def _search_language_preferences_for_tags(language_tags: tuple[str, ...]) -> tuple[str, ...]:
    return _deduplicate_languages(_language_tag_preferences(language_tags))


def _language_tag_preferences(language_tags: tuple[str, ...]) -> tuple[str, ...]:
    preferences = []
    for language_tag in language_tags or ("en-US",):
        normalized = language_tag.strip().replace("_", "-").lower()
        if normalized:
            preferences.append(normalized)
            if "-" in normalized:
                preferences.append(normalized.split("-", maxsplit=1)[0])
    return tuple(preferences)


def _deduplicate_languages(language_tags: tuple[str, ...]) -> tuple[str, ...]:
    deduplicated = []
    seen = set()
    for language in language_tags:
        if language not in seen:
            seen.add(language)
            deduplicated.append(language)
    return tuple(deduplicated)


def _pad_unknown_taxon_prediction(prediction: Prediction) -> Prediction:
    length = max(
        len(prediction.taxonomy),
        len(prediction.taxonomy_rank_names),
        len(prediction.taxonomy_common_names),
    )

    return replace(
        prediction,
        taxonomy=_pad_tuple(prediction.taxonomy, length),
        taxonomy_rank_names=_pad_tuple(prediction.taxonomy_rank_names, length),
        taxonomy_common_names=_pad_tuple(prediction.taxonomy_common_names, length),
    )


def _pad_tuple(values: tuple[str, ...], length: int) -> tuple[str, ...]:
    return values + ("",) * (length - len(values))
