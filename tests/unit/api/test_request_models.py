from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from wild_catalog.api.request_models import ExifOverrideRequest, IdentifyRequest


def test_identify_request_uses_api_defaults() -> None:
    request = IdentifyRequest(original_filename="trail-camera.jpg")

    assert request.original_filename == "trail-camera.jpg"
    assert request.exif_override is None
    assert request.return_detected_images is False
    assert request.common_name_language == "en-US"


def test_identify_request_accepts_exif_override() -> None:
    request = IdentifyRequest.model_validate(
        {
            "original_filename": "fox.raw",
            "exif_override": {
                "gps_coordinates": "45.1234, -93.1234",
                "captured_at": "2026-05-01T12:30:00Z",
            },
            "return_detected_images": True,
            "common_name_language": "es-MX",
        }
    )

    assert request.exif_override == ExifOverrideRequest(
        gps_coordinates="45.1234, -93.1234",
        captured_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
    )
    assert request.return_detected_images is True
    assert request.common_name_language == "es-MX"


@pytest.mark.parametrize(
    "gps_coordinates",
    [
        "45,-93",
        "45.0",
        "north, west",
        "45.0; -93.0",
    ],
)
def test_exif_override_rejects_invalid_gps_coordinates(gps_coordinates: str) -> None:
    with pytest.raises(ValidationError):
        ExifOverrideRequest(gps_coordinates=gps_coordinates)
