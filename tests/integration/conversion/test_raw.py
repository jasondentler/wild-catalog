from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from wild_catalog.conversion.exceptions import InvalidImageError
from wild_catalog.conversion.service import ImageConversionService

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_IMAGES = PROJECT_ROOT / "sample-images"
SAMPLE_CR3 = SAMPLE_IMAGES / "20260525-IMG_7906.CR3"
SAMPLE_DNG = SAMPLE_IMAGES / "20260525-IMG_7906.dng"

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)

requires_sample_images = pytest.mark.skipif(
    not SAMPLE_IMAGES.exists(),
    reason="Sample images are not available.",
)

requires_rawpy_decoder = pytest.mark.skipif(
    not (SAMPLE_CR3.exists() and SAMPLE_DNG.exists()),
    reason="Sample raw images are not available.",
)


def make_service(
    *,
    max_image_pixels: int = 80_000_000,
) -> ImageConversionService:
    settings = SimpleNamespace(
        max_upload_bytes=100_000_000,
        max_image_pixels=max_image_pixels,
    )
    return ImageConversionService(settings)


@requires_enabled_integration_suite
@requires_sample_images
@requires_rawpy_decoder
def test_sample_cr3_converts_to_rgb_image() -> None:
    with SAMPLE_CR3.open("rb") as image_file:
        try:
            result = make_service().process_and_extract_metadata(
                image_file=image_file,
                original_filename=SAMPLE_CR3.name,
            )
        except InvalidImageError as exc:
            pytest.skip(f"Installed rawpy/libraw cannot decode sample CR3: {exc}")

    assert result.image.mode == "RGB"
    assert result.image.width > 0
    assert result.image.height > 0
    assert result.detected_format == "cr3"
    assert result.original_filename == SAMPLE_CR3.name


@requires_enabled_integration_suite
@requires_sample_images
@requires_rawpy_decoder
def test_sample_dng_converts_to_rgb_image() -> None:
    with SAMPLE_DNG.open("rb") as image_file:
        try:
            result = make_service().process_and_extract_metadata(
                image_file=image_file,
                original_filename=SAMPLE_DNG.name,
            )
        except InvalidImageError as exc:
            pytest.skip(f"Installed rawpy/libraw cannot decode sample DNG: {exc}")

    assert result.image.mode == "RGB"
    assert result.image.width > 0
    assert result.image.height > 0
    assert result.detected_format == "dng"
    assert result.original_filename == SAMPLE_DNG.name
