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
        self._taxon_by_scientific_name: dict[str, TaxonRecord] | None = None
        self._species_by_family_and_epithet_key: dict[tuple[str, str], TaxonRecord] | None = None

    def resolve_class_index(self, class_index: ClassIndex) -> ClassIndex:
        return ClassIndex(
            id=class_index.id,
            taxon_id_by_class_id={
                class_id: self._taxon_id_for_class_id(class_id, class_index)
                for class_id in class_index.taxon_id_by_class_id
            },
            scientific_name_by_class_id=class_index.scientific_name_by_class_id,
            taxonomy_path_by_class_id=class_index.taxonomy_path_by_class_id,
        )

    def enrich_predictions(
        self,
        predictions: Sequence[ClassPrediction],
        class_index: ClassIndex,
        common_name_language: str,
        presence_by_taxon_id: Mapping[int, bool],
    ) -> list[EnrichedPrediction]:
        enriched_predictions: list[EnrichedPrediction] = []

        for prediction in predictions:
            taxon_id = self._taxon_id_for_class_prediction(
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
                raise ValueError(f"Taxonomy parent cycle detected at taxon {current_taxon_id}.")

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
        self,
        prediction: ClassPrediction,
        class_index: ClassIndex,
    ) -> int:
        return self._taxon_id_for_class_id(prediction.class_id, class_index)

    def _taxon_id_for_class_id(
        self,
        class_id: int,
        class_index: ClassIndex,
    ) -> int:
        model_scientific_name = class_index.scientific_name_by_class_id.get(class_id)

        if model_scientific_name is not None:
            resolved_taxon = self._resolve_model_taxonomy(
                scientific_name=model_scientific_name,
                taxonomy_path=class_index.taxonomy_path_by_class_id.get(
                    class_id,
                    (),
                ),
            )

            if resolved_taxon is not None:
                return resolved_taxon.taxon_id

        try:
            return class_index.taxon_id_by_class_id[class_id]
        except KeyError as exc:
            raise ValueError(f"Unknown classifier class ID: {class_id}") from exc

    def _resolve_model_taxonomy(
        self,
        *,
        scientific_name: str,
        taxonomy_path: tuple[str, ...],
    ) -> TaxonRecord | None:
        exact_match = self._find_taxon_by_scientific_name(scientific_name)

        if exact_match is not None:
            return exact_match

        return self._find_species_by_family_and_epithet(
            family_name=_family_name_from_taxonomy_path(taxonomy_path),
            specific_epithet=_specific_epithet_from_scientific_name(scientific_name),
        )

    def _find_taxon_by_scientific_name(self, scientific_name: str) -> TaxonRecord | None:
        return self._get_taxon_by_scientific_name().get(scientific_name.casefold())

    def _find_species_by_family_and_epithet(
        self,
        *,
        family_name: str | None,
        specific_epithet: str | None,
    ) -> TaxonRecord | None:
        if family_name is None or specific_epithet is None:
            return None

        return self._get_species_by_family_and_epithet_key().get(
            (_normalize_taxonomy_name(family_name), _specific_epithet_key(specific_epithet))
        )

    def _get_taxon_by_scientific_name(self) -> dict[str, TaxonRecord]:
        if self._taxon_by_scientific_name is None:
            self._taxon_by_scientific_name = {
                taxon.scientific_name.casefold(): taxon for taxon in self._store.iter_taxa()
            }

        return self._taxon_by_scientific_name

    def _get_species_by_family_and_epithet_key(
        self,
    ) -> dict[tuple[str, str], TaxonRecord]:
        if self._species_by_family_and_epithet_key is not None:
            return self._species_by_family_and_epithet_key

        species_by_key: dict[tuple[str, str], TaxonRecord] = {}

        for taxon in self._store.iter_taxa():
            if taxon.rank != "species":
                continue

            candidate_epithet = _specific_epithet_from_scientific_name(taxon.scientific_name)
            if candidate_epithet is None:
                continue

            family_name = self._family_name_for_taxon(taxon.taxon_id)
            if family_name is None:
                continue

            species_by_key.setdefault(
                (
                    _normalize_taxonomy_name(family_name),
                    _specific_epithet_key(candidate_epithet),
                ),
                taxon,
            )

        self._species_by_family_and_epithet_key = species_by_key
        return species_by_key

    def _family_name_for_taxon(self, taxon_id: int) -> str | None:
        try:
            lineage = self._build_lineage(taxon_id)
        except ValueError:
            return None

        for rank, scientific_name in zip(
            lineage.ranks,
            lineage.scientific_names,
            strict=True,
        ):
            if rank == "family":
                return scientific_name

        return _family_name_from_taxonomy_path(lineage.scientific_names)


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

    exact_matches = tuple(
        record
        for record in common_names
        if _normalize_locale(record.locale) == normalized_requested_locale
    )
    if exact_matches:
        return _best_common_name(exact_matches)

    language_matches = tuple(
        record
        for record in common_names
        if _language_from_locale(record.locale) == requested_language
    )
    if language_matches:
        return _best_common_name(language_matches)

    default_matches = tuple(
        record
        for record in common_names
        if _normalize_locale(record.locale) == normalized_default_locale
    )
    if default_matches:
        return _best_common_name(default_matches)

    english_matches = tuple(
        record for record in common_names if _language_from_locale(record.locale) == "en"
    )
    if english_matches:
        return _best_common_name(english_matches)

    return scientific_name


def _best_common_name(common_names: tuple[CommonNameRecord, ...]) -> str:
    return max(common_names, key=lambda record: (record.created != "", record.created)).name


def _family_name_from_taxonomy_path(taxonomy_path: tuple[str, ...]) -> str | None:
    for name in taxonomy_path:
        if name.endswith("idae"):
            return name

    return None


def _normalize_taxonomy_name(name: str) -> str:
    return name.casefold()


def _specific_epithet_from_scientific_name(scientific_name: str) -> str | None:
    parts = scientific_name.split()

    if len(parts) < 2:
        return None

    return parts[1]


def _specific_epithet_key(specific_epithet: str) -> str:
    normalized_epithet = specific_epithet.casefold()

    for suffix in ("us", "um", "a"):
        if len(normalized_epithet) > len(suffix) + 3 and normalized_epithet.endswith(suffix):
            return normalized_epithet[: -len(suffix)]

    return normalized_epithet
