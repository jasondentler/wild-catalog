from __future__ import annotations

import os
from pathlib import Path

import pytest

from wild_catalog.conversion.format_sniffing import ImageFormat, sniff_image_format

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_IMAGES = PROJECT_ROOT / "sample-images"
SAMPLE_WEBP = SAMPLE_IMAGES / "20260402-IMG_7906.webp"

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)

requires_sample_images = pytest.mark.skipif(
    not SAMPLE_IMAGES.exists(),
    reason="Sample images are not available.",
)


@requires_enabled_integration_suite
@requires_sample_images
def test_sniff_image_format_detects_webp_from_real_sample() -> None:
    with SAMPLE_WEBP.open("rb") as image_file:
        assert sniff_image_format(image_file.read(), SAMPLE_WEBP.name) == ImageFormat.WEBP
