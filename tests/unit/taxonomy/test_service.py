import pytest

from wild_catalog.classifier.types import ClassIndex, ClassPrediction
from wild_catalog.core.config import Settings
from wild_catalog.taxonomy.service import TaxonomyService
from wild_catalog.taxonomy.store import InMemoryTaxonomyStore
from wild_catalog.taxonomy.types import CommonNameRecord, TaxonRecord


def make_store() -> InMemoryTaxonomyStore:
    return InMemoryTaxonomyStore(
        taxa_by_id={
            1: TaxonRecord(1, "Animalia", "kingdom", None),
            2: TaxonRecord(2, "Chordata", "phylum", 1),
            3: TaxonRecord(3, "Aves", "class", 2),
        },
        common_names_by_taxon_id={
            1: (CommonNameRecord(1, "en-US", "Animals"),),
            2: (CommonNameRecord(2, "en-US", "Chordates"),),
            3: (CommonNameRecord(3, "en-US", "Birds"),),
        },
    )


def test_enrich_predictions_maps_class_id_to_taxonomy() -> None:
    service = TaxonomyService(Settings(), store=make_store())
    class_index = ClassIndex(
        id="stub",
        taxon_id_by_class_id={0: 3},
    )

    enriched = service.enrich_predictions(
        predictions=[ClassPrediction(class_id=0, confidence=0.95)],
        class_index=class_index,
        common_name_language="en-US",
        presence_by_taxon_id={3: True},
    )

    assert len(enriched) == 1
    assert enriched[0].class_id == 0
    assert enriched[0].taxon_id == 3
    assert enriched[0].accepted_taxon_id == 3
    assert enriched[0].confidence == 0.95
    assert enriched[0].is_present is True
    assert enriched[0].taxonomy == ("Animalia", "Chordata", "Aves")
    assert enriched[0].taxonomy_common_names == ("Animals", "Chordates", "Birds")
    assert enriched[0].taxonomy_rank_names == ("kingdom", "phylum", "class")
    assert len(enriched[0].taxonomy) == len(enriched[0].taxonomy_common_names)


def test_enrich_predictions_rejects_unknown_class_id() -> None:
    service = TaxonomyService(Settings(), store=make_store())
    class_index = ClassIndex(
        id="stub",
        taxon_id_by_class_id={0: 3},
    )

    with pytest.raises(ValueError, match="Unknown classifier class ID"):
        service.enrich_predictions(
            predictions=[ClassPrediction(class_id=99, confidence=0.95)],
            class_index=class_index,
            common_name_language="en-US",
            presence_by_taxon_id={3: True},
        )


def test_enrich_predictions_resolves_accepted_taxon() -> None:
    store = InMemoryTaxonomyStore(
        taxa_by_id={
            1: TaxonRecord(1, "Animalia", "kingdom", None),
            3: TaxonRecord(3, "Aves", "class", 1),
            4: TaxonRecord(
                4,
                "Old Bird",
                "species",
                3,
                accepted_taxon_id=3,
                is_active=False,
            ),
        }
    )
    service = TaxonomyService(Settings(), store=store)
    class_index = ClassIndex(
        id="stub",
        taxon_id_by_class_id={0: 4},
    )

    enriched = service.enrich_predictions(
        predictions=[ClassPrediction(class_id=0, confidence=0.95)],
        class_index=class_index,
        common_name_language="en-US",
        presence_by_taxon_id={3: True},
    )

    assert enriched[0].taxon_id == 4
    assert enriched[0].accepted_taxon_id == 3
    assert enriched[0].is_present is True
    assert enriched[0].taxonomy[-1] == "Aves"


def test_enrich_predictions_defaults_missing_presence_to_false() -> None:
    service = TaxonomyService(Settings(), store=make_store())
    class_index = ClassIndex(
        id="stub",
        taxon_id_by_class_id={0: 3},
    )

    enriched = service.enrich_predictions(
        predictions=[ClassPrediction(class_id=0, confidence=0.95)],
        class_index=class_index,
        common_name_language="en-US",
        presence_by_taxon_id={},
    )

    assert enriched[0].is_present is False
