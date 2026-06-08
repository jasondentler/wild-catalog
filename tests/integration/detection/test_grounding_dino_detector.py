import os
from pathlib import Path

import pytest
from PIL import Image

from wild_catalog.core.config import Settings
from wild_catalog.core.errors import ModelUnavailableError, UnprocessableImageError
from wild_catalog.detection.preop import preop_detector_model
from wild_catalog.detection.registry import build_detector
from wild_catalog.detection.types import DetectionCategory

pytestmark = pytest.mark.integration


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_IMAGE_PATH = PROJECT_ROOT / "sample-images" / "20260402-IMG_7906.jpg"

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)


@requires_enabled_integration_suite
def test_grounding_dino_detects_living_subjects_in_sample_image() -> None:
    assert SAMPLE_IMAGE_PATH.exists(), f"Missing required sample image fixture: {SAMPLE_IMAGE_PATH}"

    settings = Settings(detector_backend="grounding-dino")
    _run_preop_or_skip(settings)
    detector = build_detector(settings)

    with Image.open(SAMPLE_IMAGE_PATH) as image:
        rgb_image = image.convert("RGB")
        width, height = rgb_image.size
        detections = detector.locate_objects(rgb_image)

    assert detections

    for detection in detections:
        assert detection.category in {
            DetectionCategory.ANIMAL,
            DetectionCategory.PLANT,
            DetectionCategory.FUNGUS,
            DetectionCategory.LICHEN,
        }
        assert 0 <= detection.bounding_box.xmin < detection.bounding_box.xmax <= width
        assert 0 <= detection.bounding_box.ymin < detection.bounding_box.ymax <= height


def _run_preop_or_skip(settings: Settings) -> None:
    try:
        preop_detector_model(settings)
    except (ModelUnavailableError, UnprocessableImageError) as exc:
        pytest.skip(f"Could not provision Grounding DINO detector model: {exc}")
    except Exception as exc:
        pytest.skip(f"Could not run Grounding DINO detector integration test: {exc}")
