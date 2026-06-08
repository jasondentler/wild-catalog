import os
from pathlib import Path

import pytest
from PIL import Image

from wild_catalog.classifier.preop import preop_classifier_model
from wild_catalog.classifier.registry import build_classifier
from wild_catalog.conditioning.service import LogitConditioner
from wild_catalog.conversion.exif import extract_metadata
from wild_catalog.core.config import Settings
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.prior.build.builder import build_inat21_range_map_store
from wild_catalog.prior.service import SpeciesRangePriorService
from wild_catalog.taxonomy.dwca import (
    download_taxonomy_dwca,
    load_taxonomy_store_from_dwca,
    taxonomy_dwca_path_for_settings,
)
from wild_catalog.taxonomy.preop import preop_taxonomy_dwca
from wild_catalog.taxonomy.service import TaxonomyService

pytestmark = pytest.mark.integration


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_IMAGE_PATH = PROJECT_ROOT / "sample-images" / "20260402-IMG_7906.jpg"
EXPECTED_SCIENTIFIC_NAME = "Nannopterum brasilianum"
EXPECTED_COMMON_NAME = "Neotropic Cormorant"
SAMPLE_GPS_FALLBACK = GpsCoordinates(latitude=29.574609186666667, longitude=-94.39028253166667)


requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)


@requires_enabled_integration_suite
def test_classifier_prior_conditioning_taxonomy_identifies_neotropic_cormorant() -> None:
    assert SAMPLE_IMAGE_PATH.exists(), f"Missing required sample image fixture: {SAMPLE_IMAGE_PATH}"

    settings = Settings(
        classifier_backend="birder-inat21",
        classifier_model_cache_path=Path("data/models/classifier"),
        taxonomy_dwca_path=Path("data/taxonomy/taxonomy.dwca.zip"),
        range_map_store_path=Path("data/range-maps/ranges.sqlite3"),
        prior_gamma=12.0,
        prior_epsilon=0.01,
        classifier_top_k=12,
    )
    ensure_cormorant_preop_data(settings)

    classifier = build_classifier(settings)

    with Image.open(SAMPLE_IMAGE_PATH) as image:
        rgb_image = image.convert("RGB")

    classifier_output = classifier.predict_species([rgb_image])

    taxonomy_archive_path = download_taxonomy_dwca(settings)
    taxonomy_store = load_taxonomy_store_from_dwca(taxonomy_archive_path)
    taxonomy_service = TaxonomyService(settings, store=taxonomy_store)
    resolved_class_index = taxonomy_service.resolve_class_index(classifier_output.class_index)

    gps_coordinates = sample_gps_coordinates()
    prior_service = SpeciesRangePriorService(settings)
    prior_mask = prior_service.generate_prior_mask(
        gps_coordinates=gps_coordinates,
        class_index=resolved_class_index,
    )

    conditioner = LogitConditioner(
        gamma=settings.prior_gamma,
        epsilon=settings.prior_epsilon,
        top_k=settings.classifier_top_k,
    )
    predictions_by_crop = conditioner.apply_geographic_prior(
        classifier_output=classifier_output,
        prior_mask=prior_mask,
    )
    top_predictions = predictions_by_crop[0]

    top_taxon_ids = {
        resolved_class_index.taxon_id_by_class_id[prediction.class_id]
        for prediction in top_predictions
    }
    presence = prior_service.get_presence_for_taxa(
        gps_coordinates=gps_coordinates,
        taxon_ids=top_taxon_ids,
    )

    enriched_predictions = taxonomy_service.enrich_predictions(
        predictions=top_predictions,
        class_index=resolved_class_index,
        common_name_language="en-US",
        presence_by_taxon_id=presence.is_present_by_taxon_id,
    )

    assert enriched_predictions

    top_prediction = enriched_predictions[0]

    assert top_prediction.taxonomy[-1] == EXPECTED_SCIENTIFIC_NAME
    assert top_prediction.taxonomy_common_names[-1] == EXPECTED_COMMON_NAME
    assert top_prediction.is_present is True


def sample_gps_coordinates() -> GpsCoordinates:
    with SAMPLE_IMAGE_PATH.open("rb") as image_file:
        metadata = extract_metadata(image_file)

    return metadata.gps_coordinates or SAMPLE_GPS_FALLBACK


def ensure_cormorant_preop_data(settings: Settings) -> None:
    taxonomy_archive_path = taxonomy_dwca_path_for_settings(settings)
    if not taxonomy_archive_path.exists() or taxonomy_archive_path.stat().st_size == 0:
        _run_preop_or_skip(
            lambda: preop_taxonomy_dwca(settings),
            artifact_name="taxonomy DarwinCore Archive",
        )

    if settings.range_map_store_path is None:
        raise ValueError("Cormorant integration test requires a range-map store path.")

    if (
        not settings.range_map_store_path.exists()
        or settings.range_map_store_path.stat().st_size == 0
    ):
        _run_preop_or_skip(
            lambda: build_inat21_range_map_store(settings),
            artifact_name="iNat21 range-map store",
        )

    _run_preop_or_skip(
        lambda: preop_classifier_model(settings),
        artifact_name="Birder iNat21 classifier model",
    )


def _run_preop_or_skip(action, *, artifact_name: str) -> None:
    try:
        action()
    except Exception as exc:
        pytest.skip(f"Could not provision {artifact_name}: {exc}")
