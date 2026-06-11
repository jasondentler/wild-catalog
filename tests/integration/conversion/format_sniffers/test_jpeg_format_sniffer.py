from __future__ import annotations

import os
from pathlib import Path

import pytest

from wild_catalog.conversion.format_sniffing import ImageFormat, sniff_image_format

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_IMAGES = PROJECT_ROOT / "sample-images"
SAMPLE_JPEG = SAMPLE_IMAGES / "20260419-DA8A0090.jpg"

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
def test_sniff_image_format_detects_jpeg_from_real_sample() -> None:
    with SAMPLE_JPEG.open("rb") as image_file:
        assert sniff_image_format(image_file.read(), SAMPLE_JPEG.name) == ImageFormat.JPEG
