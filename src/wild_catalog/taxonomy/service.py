from collections.abc import Mapping, Sequence

from wild_catalog.classifier.types import ClassIndex, ClassPrediction
from wild_catalog.core.config import Settings
from wild_catalog.taxonomy.protocols import TaxonomyServiceProtocol
from wild_catalog.taxonomy.store import TaxonomyStore
from wild_catalog.taxonomy.stub import build_stub_taxonomy_store
from wild_catalog.taxonomy.types import (
    CommonNameRecord,
    EnrichedPrediction,
    TaxonLineage,
    TaxonRecord,
)


class TaxonomyService(TaxonomyServiceProtocol):
    def __init__(
        self,
        settings: Settings,
        store: TaxonomyStore | None = None,
    ) -> None:
        self._settings = settings
        self._default_locale = settings.taxonomy_default_language
        self._store = store or build_stub_taxonomy_store()

    def enrich_predictions(
        self,
        predictions: Sequence[ClassPrediction],
        class_index: ClassIndex,
        common_name_language: str,
        presence_by_taxon_id: Mapping[int, bool],
    ) -> list[EnrichedPrediction]:
        enriched_predictions: list[EnrichedPrediction] = []

        for prediction in predictions:
            taxon_id = _taxon_id_for_class_prediction(
                prediction,
                class_index,
            )
            accepted_taxon = self._resolve_accepted_taxon(taxon_id)
            lineage = self._build_lineage(accepted_taxon.taxon_id)

            taxonomy_common_names = tuple(
                self._common_name_for_taxon_id(
                    taxon_id=lineage_taxon_id,
                    scientific_name=scientific_name,
                    requested_locale=common_name_language,
                )
                for lineage_taxon_id, scientific_name in zip(
                    lineage.taxon_ids,
                    lineage.scientific_names,
                    strict=True,
                )
            )

            enriched_predictions.append(
                EnrichedPrediction(
                    class_id=prediction.class_id,
                    taxon_id=taxon_id,
                    accepted_taxon_id=accepted_taxon.taxon_id,
                    confidence=prediction.confidence,
                    is_present=presence_by_taxon_id.get(accepted_taxon.taxon_id, False),
                    taxonomy=lineage.scientific_names,
                    taxonomy_common_names=taxonomy_common_names,
                    taxonomy_rank_names=lineage.ranks,
                )
            )

        return enriched_predictions

    def _resolve_accepted_taxon(self, taxon_id: int) -> TaxonRecord:
        taxon = self._get_required_taxon(taxon_id)

        if taxon.accepted_taxon_id is None:
            return taxon

        return self._get_required_taxon(taxon.accepted_taxon_id)

    def _build_lineage(self, taxon_id: int) -> TaxonLineage:
        lineage_records: list[TaxonRecord] = []
        seen_taxon_ids: set[int] = set()
        current_taxon_id: int | None = taxon_id

        while current_taxon_id is not None:
            if current_taxon_id in seen_taxon_ids:
                raise ValueError(
                    f"Taxonomy parent cycle detected at taxon {current_taxon_id}."
                )

            seen_taxon_ids.add(current_taxon_id)

            taxon = self._get_required_taxon(current_taxon_id)
            lineage_records.append(taxon)
            current_taxon_id = taxon.parent_taxon_id

        lineage_records.reverse()

        return TaxonLineage(
            taxon_ids=tuple(record.taxon_id for record in lineage_records),
            scientific_names=tuple(record.scientific_name for record in lineage_records),
            ranks=tuple(record.rank for record in lineage_records),
        )

    def _common_name_for_taxon_id(
        self,
        *,
        taxon_id: int,
        scientific_name: str,
        requested_locale: str,
    ) -> str:
        common_names = self._store.get_common_names(taxon_id)

        return _select_common_name(
            common_names=common_names,
            scientific_name=scientific_name,
            requested_locale=requested_locale,
            default_locale=self._default_locale,
        )

    def _get_required_taxon(self, taxon_id: int) -> TaxonRecord:
        taxon = self._store.get_taxon(taxon_id)

        if taxon is None:
            raise ValueError(f"Unknown taxon ID: {taxon_id}")

        return taxon


def _taxon_id_for_class_prediction(
    prediction: ClassPrediction,
    class_index: ClassIndex,
) -> int:
    try:
        return class_index.taxon_id_by_class_id[prediction.class_id]
    except KeyError as exc:
        raise ValueError(f"Unknown classifier class ID: {prediction.class_id}") from exc


def _language_from_locale(locale: str) -> str:
    return locale.split("-", maxsplit=1)[0].split("_", maxsplit=1)[0].lower()


def _normalize_locale(locale: str) -> str:
    return locale.strip().replace("_", "-").lower()


def _select_common_name(
    *,
    common_names: tuple[CommonNameRecord, ...],
    scientific_name: str,
    requested_locale: str,
    default_locale: str,
) -> str:
    normalized_requested_locale = _normalize_locale(requested_locale)
    requested_language = _language_from_locale(normalized_requested_locale)
    normalized_default_locale = _normalize_locale(default_locale)

    by_locale = {_normalize_locale(record.locale): record.name for record in common_names}

    exact_match = by_locale.get(normalized_requested_locale)
    if exact_match is not None:
        return exact_match

    for record in common_names:
        if _language_from_locale(record.locale) == requested_language:
            return record.name

    default_match = by_locale.get(normalized_default_locale)
    if default_match is not None:
        return default_match

    for record in common_names:
        if _language_from_locale(record.locale) == "en":
            return record.name

    return scientific_name
