import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.settings import Settings
from wild_catalog.core.types import BoundingBox, Detection, GpsCoordinates
from wild_catalog.image_cropper.image_cropping import ImageCropper
from wild_catalog.logit_conditioning import LogitConditioner
from wild_catalog.range_data import (
    import_geopackages,
    import_inaturalist_open_range_data_if_missing,
)
from wild_catalog.range_data.species_range_prior_service import SpeciesRangePriorService
from wild_catalog.species_classifier.classifier import BirderSpeciesClassifier

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_DNG = PROJECT_ROOT / "sample-images" / "20260525-IMG_7906.dng"
RANGE_STORE = PROJECT_ROOT / "data" / "range-data" / "inaturalist-open-range-store.sqlite"
GEOPACKAGE_DIR = PROJECT_ROOT / "data" / "range-data" / "geopackages"
EXPECTED_LABEL = (
    "03867_Animalia_Chordata_Aves_Passeriformes_Icteridae_Agelaius_phoeniceus"
)
HOUSTON_GPS = GpsCoordinates(latitude=29.7604, longitude=-95.3698)
RED_WINGED_BLACKBIRD_TAXON_ID = 145236
TRICOLORED_BLACKBIRD_CLASS_ID = 3868
RED_WINGED_BLACKBIRD_CLASS_ID = 3867

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)


@requires_enabled_integration_suite
def test_houston_range_prior_promotes_red_winged_blackbird_for_sample_dng() -> None:
    _ensure_local_assets()

    with SAMPLE_DNG.open("rb") as image_file:
        converted_image = ImageConversionService(
            SimpleNamespace(
                max_upload_bytes=100_000_000,
                max_image_pixels=120_000_000,
            ),
        ).process_and_extract_metadata(
            image_file=image_file,
            original_filename=SAMPLE_DNG.name,
        )

    crop = ImageCropper(Settings()).crop(
        converted_image.image,
        Detection(
            box=BoundingBox(xmin=2542, ymin=1826, xmax=2755, ymax=2155),
            confidence=1.0,
            class_id=0,
        ),
    ).cropped_image
    classifier = BirderSpeciesClassifier(
        Settings(species_classifier_top_k=5),
        device="cpu",
        taxon_id_by_class_id={3867: RED_WINGED_BLACKBIRD_TAXON_ID},
    )
    raw_output = classifier.classify_raw(crop)
    raw_top_class_id = int(raw_output.probabilities[0].argmax().detach().cpu())

    with SpeciesRangePriorService(
        SimpleNamespace(
            prior_epsilon=0.01,
            range_prior_cache_enabled=False,
            range_prior_cache_max_entries=10,
            range_prior_cache_h3_resolution=7,
            range_store_database_path=RANGE_STORE,
        ),
    ) as range_prior_service:
        prior_mask = range_prior_service.generate_prior_mask(
            HOUSTON_GPS,
            raw_output.class_index,
        )
    predictions = LogitConditioner(
        gamma=2.0,
        epsilon=1e-12,
        top_k=5,
    ).apply_geographic_prior(raw_output, prior_mask)[0]

    assert raw_top_class_id == TRICOLORED_BLACKBIRD_CLASS_ID
    assert predictions[0].class_id == RED_WINGED_BLACKBIRD_CLASS_ID
    assert predictions[0].taxonomy == (EXPECTED_LABEL,)
    assert predictions[0].taxon_id == RED_WINGED_BLACKBIRD_TAXON_ID
    assert predictions[0].is_present is True


def _ensure_local_assets() -> None:
    if not SAMPLE_DNG.exists():
        raise FileNotFoundError(f"Sample DNG is required for this test: {SAMPLE_DNG}")

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
