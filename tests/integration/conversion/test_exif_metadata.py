import os
from datetime import datetime
from pathlib import Path

import pytest

from wild_catalog.conversion.exif import extract_metadata

pytestmark = pytest.mark.integration

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_IMAGES = PROJECT_ROOT / "sample-images"
SAMPLE_WITH_GPS = SAMPLE_IMAGES / "20260402-IMG_7906.jpg"
SAMPLE_WITHOUT_GPS = SAMPLE_IMAGES / "20260419-DA8A5506.jpg"

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)


@requires_enabled_integration_suite
@pytest.mark.skipif(not SAMPLE_WITH_GPS.exists(), reason="GPS sample image is not available.")
def test_extract_metadata_reads_gps_coordinates_from_sample_image() -> None:
    with SAMPLE_WITH_GPS.open("rb") as image_file:
        metadata = extract_metadata(image_file)

        assert image_file.tell() == 0

    assert metadata.gps_coordinates is not None
    assert metadata.gps_coordinates.latitude == pytest.approx(29.574609186666667)
    assert metadata.gps_coordinates.longitude == pytest.approx(-94.39028253166667)
    assert metadata.captured_at == datetime(2026, 4, 2, 17, 34, 8)


@requires_enabled_integration_suite
@pytest.mark.skipif(not SAMPLE_WITHOUT_GPS.exists(), reason="No-GPS sample image is not available.")
def test_extract_metadata_returns_none_when_sample_image_has_no_gps_coordinates() -> None:
    with SAMPLE_WITHOUT_GPS.open("rb") as image_file:
        metadata = extract_metadata(image_file)

        assert image_file.tell() == 0

    assert metadata.gps_coordinates is None
    assert metadata.captured_at == datetime(2026, 4, 19, 8, 31, 35)
