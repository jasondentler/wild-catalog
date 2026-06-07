import os
import platform
from pathlib import Path

import pytest

from wild_catalog.conversion.exceptions import PlatformConversionError
from wild_catalog.conversion.platform_conversion.windows_imagemagick import (
    WindowsImageMagickImageConverter,
)
from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.config import Settings

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_HEIC = PROJECT_ROOT / "sample-images" / "20260525-IMG_7906.heic"

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)

requires_windows = pytest.mark.skipif(
    platform.system().lower() != "windows",
    reason="Windows ImageMagick HEIC conversion test runs only on Windows.",
)

requires_sample_heic = pytest.mark.skipif(
    not SAMPLE_HEIC.exists(),
    reason="Sample HEIC image is not available.",
)


def make_service() -> ImageConversionService:
    return ImageConversionService(
        Settings(
            max_upload_bytes=100_000_000,
            max_image_pixels=80_000_000,
            platform_image_converter="windows-imagemagick",
            platform_conversion_timeout_seconds=20,
        )
    )


@requires_enabled_integration_suite
@requires_windows
@requires_sample_heic
def test_sample_heic_converts_with_windows_imagemagick() -> None:
    if not WindowsImageMagickImageConverter(timeout_seconds=20).can_convert("heic"):
        pytest.skip("ImageMagick magick utility is not available for HEIC conversion.")

    with SAMPLE_HEIC.open("rb") as image_file:
        try:
            result = make_service().process_and_extract_metadata(
                image_file=image_file,
                original_filename=SAMPLE_HEIC.name,
            )
        except PlatformConversionError as exc:
            pytest.skip(f"ImageMagick could not convert sample HEIC: {exc}")

    assert result.image.mode == "RGB"
    assert result.image.width > 0
    assert result.image.height > 0
    assert result.detected_format == "heic"
