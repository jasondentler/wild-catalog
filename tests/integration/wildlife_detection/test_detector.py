from __future__ import annotations

import os
from pathlib import Path
from urllib.error import URLError

import pytest
from PIL import Image

from wild_catalog.core.settings import MDV6_APACHE_RTDETR_E_URL
from wild_catalog.core.types import Detection
from wild_catalog.wildlife_detection.detector import DEFAULT_MODEL_PATH, WildlifeDetector
from wild_catalog.wildlife_detection.model_download import download_file_with_progress

MODEL_PATH = DEFAULT_MODEL_PATH
MODEL_URL = os.getenv(
    "WILD_CATALOG_DETECTOR_MODEL_URL",
    MDV6_APACHE_RTDETR_E_URL,
)
SAMPLE_IMAGES_DIR = Path("sample-images")


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
        reason="Skipping integration test suite. Run 'make test' to execute.",
    ),
]


@pytest.fixture(scope="module")
def detector_model_path() -> Path:
    if MODEL_PATH.exists():
        return MODEL_PATH

    try:
        download_file_with_progress(MODEL_URL, MODEL_PATH)
    except (OSError, URLError) as exc:
        pytest.fail(f"Failed to download detector model from {MODEL_URL}: {exc}")

    return MODEL_PATH


@pytest.fixture(scope="module")
def detector(detector_model_path: Path) -> WildlifeDetector:
    assert detector_model_path == MODEL_PATH
    return WildlifeDetector(model_weights=detector_model_path)


@pytest.mark.parametrize(
    "image_path",
    [
        SAMPLE_IMAGES_DIR / "20260402-IMG_7906.jpg",
        SAMPLE_IMAGES_DIR / "20260402-IMG_7906.png",
        SAMPLE_IMAGES_DIR / "20260402-IMG_7906.webp",
        SAMPLE_IMAGES_DIR / "20260419-DA8A0090.jpg",
        SAMPLE_IMAGES_DIR / "20260419-DA8A5083.jpg",
        SAMPLE_IMAGES_DIR / "20260419-DA8A5151.jpg",
        SAMPLE_IMAGES_DIR / "20260419-DA8A5506.jpg",
        SAMPLE_IMAGES_DIR / "20260419-DA8A7718.jpg",
    ],
)
def test_detector_runs_against_sample_image(
    detector: WildlifeDetector,
    image_path: Path,
) -> None:
    with Image.open(image_path) as image:
        detections = detector.detect(image.convert("RGB"))

    assert isinstance(detections, list)
    for detection in detections:
        assert isinstance(detection, Detection)
        assert detection.box.width > 0
        assert detection.box.height > 0
        assert detection.confidence > 0.3
        assert isinstance(detection.class_id, int)
