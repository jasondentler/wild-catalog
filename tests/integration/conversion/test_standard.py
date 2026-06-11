from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from wild_catalog.conversion.service import ImageConversionService

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_IMAGES = PROJECT_ROOT / "sample-images"
SAMPLE_JPEGS = tuple(sorted(SAMPLE_IMAGES.glob("*.jpg")))
SAMPLE_PNG = SAMPLE_IMAGES / "20260402-IMG_7906.png"
SAMPLE_WEBP = SAMPLE_IMAGES / "20260402-IMG_7906.webp"

requires_sample_images = pytest.mark.skipif(
    not SAMPLE_IMAGES.exists(),
    reason="Sample images are not available.",
)

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
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
@pytest.mark.parametrize("image_path", SAMPLE_JPEGS, ids=lambda path: path.name)
def test_sample_jpegs_convert_to_rgb_images(image_path: Path) -> None:
    with image_path.open("rb") as image_file:
        result = make_service().process_and_extract_metadata(
            image_file=image_file,
            original_filename=image_path.name,
        )

    assert result.image.mode == "RGB"
    assert result.image.width > 0
    assert result.image.height > 0
    assert result.detected_format == "jpeg"
    assert result.original_filename == image_path.name


@requires_enabled_integration_suite
@requires_sample_images
def test_sample_png_converts_to_rgb_image() -> None:
    with SAMPLE_PNG.open("rb") as image_file:
        result = make_service().process_and_extract_metadata(
            image_file=image_file,
            original_filename=SAMPLE_PNG.name,
        )

    assert result.image.mode == "RGB"
    assert result.image.width > 0
    assert result.image.height > 0
    assert result.detected_format == "png"
    assert result.original_filename == SAMPLE_PNG.name


@requires_enabled_integration_suite
@requires_sample_images
def test_sample_webp_converts_to_rgb_image() -> None:
    with SAMPLE_WEBP.open("rb") as image_file:
        result = make_service().process_and_extract_metadata(
            image_file=image_file,
            original_filename=SAMPLE_WEBP.name,
        )

    assert result.image.mode == "RGB"
    assert result.image.width > 0
    assert result.image.height > 0
    assert result.detected_format == "webp"
    assert result.original_filename == SAMPLE_WEBP.name
