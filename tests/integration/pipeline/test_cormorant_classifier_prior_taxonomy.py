import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from wild_catalog.core.settings import Settings
from wild_catalog.core.types import BoundingBox, Detection, GpsCoordinates
from wild_catalog.detection_processing_pipeline.detection_processing_pipeline import (
    DetectionProcessingPipeline,
)
from wild_catalog.image_cropper.image_cropping import ImageCropper
from wild_catalog.logit_conditioning import LogitConditioner
from wild_catalog.range_data import (
    import_geopackages,
    import_inaturalist_open_range_data_if_missing,
)
from wild_catalog.range_data.species_range_prior_service import SpeciesRangePriorService
from wild_catalog.species_classifier.classifier import BirderSpeciesClassifier
from wild_catalog.taxonomy import (
    SQLiteTaxonomyStore,
    TaxonomyService,
    import_taxonomy_archive_if_missing,
    local_then_inaturalist_taxon_lookup,
)

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_IMAGE = PROJECT_ROOT / "sample-images" / "20260402-IMG_7906.jpg"
RANGE_STORE = PROJECT_ROOT / "data" / "range-data" / "inaturalist-open-range-store.sqlite"
GEOPACKAGE_DIR = PROJECT_ROOT / "data" / "range-data" / "geopackages"
TAXONOMY_STORE = PROJECT_ROOT / "data" / "taxonomy" / "inaturalist-taxonomy-store.sqlite"
TAXONOMY_DIR = PROJECT_ROOT / "data" / "taxonomy"
NEOTROPIC_CORMORANT_TAXON_ID = 1289601
OLD_NEOTROPIC_CORMORANT_NAME = "Phalacrocorax brasilianus"
EXPECTED_CLASS_LABEL = (
    "04575_Animalia_Chordata_Aves_Suliformes_Phalacrocoracidae_"
    "Phalacrocorax_brasilianus"
)
SAMPLE_GPS = GpsCoordinates(
    latitude=29 + 34.4765512 / 60,
    longitude=-(94 + 23.4169519 / 60),
)

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)


@requires_enabled_integration_suite
def test_neotropic_cormorant_uses_active_inaturalist_taxon_for_range_and_taxonomy() -> None:
    _ensure_local_assets()
    api_lookup_requests: list[tuple[str, ...]] = []

    taxonomy_store = SQLiteTaxonomyStore(TAXONOMY_STORE)
    range_prior_service = SpeciesRangePriorService(
        SimpleNamespace(
            prior_epsilon=0.01,
            range_prior_cache_enabled=False,
            range_prior_cache_max_entries=10,
            range_prior_cache_h3_resolution=7,
            range_store_database_path=RANGE_STORE,
        )
    )
    try:
        classifier = BirderSpeciesClassifier(
            Settings(species_classifier_top_k=10),
            device="cpu",
            taxon_id_by_scientific_name=local_then_inaturalist_taxon_lookup(
                taxonomy_store.get_taxon_ids_by_scientific_names,
                _active_taxon_api_lookup(api_lookup_requests),
            ),
        )
        pipeline = DetectionProcessingPipeline(
            ImageCropper(Settings()),
            classifier,
            range_prior_service=range_prior_service,
            logit_conditioner=LogitConditioner(
                gamma=2.0,
                epsilon=1e-12,
                top_k=10,
            ),
            taxonomy_service=TaxonomyService(taxonomy_store),
        )

        with Image.open(SAMPLE_IMAGE) as image:
            identified_object = pipeline.process(
                image,
                Detection(
                    box=BoundingBox(
                        xmin=0,
                        ymin=0,
                        xmax=image.width,
                        ymax=image.height,
                    ),
                    confidence=1.0,
                    class_id=0,
                ),
                SAMPLE_GPS,
            )
    finally:
        range_prior_service.close()
        taxonomy_store.close()

    top_prediction = identified_object.predictions[0]

    assert any(
        OLD_NEOTROPIC_CORMORANT_NAME in request for request in api_lookup_requests
    )
    assert top_prediction.class_id == 4575
    assert top_prediction.taxon_id == NEOTROPIC_CORMORANT_TAXON_ID
    assert top_prediction.accepted_taxon_id == NEOTROPIC_CORMORANT_TAXON_ID
    assert top_prediction.is_present is True
    assert top_prediction.confidence >= 0.99
    assert top_prediction.taxonomy[-3:] == (
        "Phalacrocoracidae",
        "Nannopterum",
        "brasilianum",
    )
    assert top_prediction.taxonomy_rank_names[-3:] == ("family", "genus", "species")
    assert identified_object.predictions[0].taxonomy != (EXPECTED_CLASS_LABEL,)


def _active_taxon_api_lookup(api_lookup_requests: list[tuple[str, ...]]):
    def lookup(scientific_names) -> dict[str, int]:
        requested_names = tuple(scientific_names)
        api_lookup_requests.append(requested_names)
        if OLD_NEOTROPIC_CORMORANT_NAME in requested_names:
            return {
                OLD_NEOTROPIC_CORMORANT_NAME: NEOTROPIC_CORMORANT_TAXON_ID,
            }
        return {}

    return lookup


def _ensure_local_assets() -> None:
    if not SAMPLE_IMAGE.exists():
        raise FileNotFoundError(f"Sample image is required for this test: {SAMPLE_IMAGE}")

    if not TAXONOMY_STORE.exists():
        import_taxonomy_archive_if_missing(TAXONOMY_STORE, TAXONOMY_DIR)

    if RANGE_STORE.exists():
        return

    RANGE_STORE.parent.mkdir(parents=True, exist_ok=True)
    geopackage_paths = sorted(GEOPACKAGE_DIR.glob("*.gpkg"))
    if geopackage_paths:
        import_geopackages(
            RANGE_STORE,
            geopackage_paths,
            metadata={"source": "cached-test-geopackages"},
        )
        return

    import_inaturalist_open_range_data_if_missing(RANGE_STORE, GEOPACKAGE_DIR)
