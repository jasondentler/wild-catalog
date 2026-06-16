from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from wild_catalog.api.request_models import (
    ExifOverrideRequest,
    GpsCoordinatesRequest,
    IdentifyRequest,
)


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
                "gps_coordinates": {
                    "latitude": 45.1234,
                    "longitude": -93.1234,
                },
                "captured_at": "2026-05-01T12:30:00Z",
            },
            "return_detected_images": True,
            "common_name_language": "es-MX",
        }
    )

    assert request.exif_override == ExifOverrideRequest(
        gps_coordinates=GpsCoordinatesRequest(latitude=45.1234, longitude=-93.1234),
        captured_at=datetime(2026, 5, 1, 12, 30, tzinfo=UTC),
    )
    assert request.return_detected_images is True
    assert request.common_name_language == "es-MX"


def test_identify_request_parses_json_string_payload() -> None:
    request = IdentifyRequest.model_validate(
        """
        {
          "original_filename": "camera-trap.jpg",
          "return_detected_images": true,
          "common_name_language": "fr-FR"
        }
        """
    )

    assert request.original_filename == "camera-trap.jpg"
    assert request.return_detected_images is True
    assert request.common_name_language == "fr-FR"


def test_identify_request_accepts_legacy_gps_coordinate_string() -> None:
    request = IdentifyRequest.model_validate(
        {
            "original_filename": "fox.raw",
            "exif_override": {
                "gps_coordinates": "45.1234, -93.1234",
            },
        }
    )

    assert request.exif_override == ExifOverrideRequest(
        gps_coordinates="45.1234, -93.1234",
    )


@pytest.mark.parametrize(
    "gps_coordinates",
    [
        '29°34\'24.1"N, 94°23\'22.2"W',
        '29°34\'24.1"N 94°23\'22.2"W',
        "29 34 24.1 N, 94 23 22.2 W",
        "29 34 24.1 N 94 23 22.2 W",
        "29°34.4017'N, 94°23.37'W",
        "29.573361 -94.389507",
        "N 29 34 24.1 W 94 23 22.2",
        '29°43\'7.806" N 95°37\'39.612" W',
    ],
)
def test_identify_request_accepts_dms_gps_coordinate_string(
    gps_coordinates: str,
) -> None:
    request = IdentifyRequest.model_validate(
        {
            "original_filename": "fox.raw",
            "exif_override": {
                "gps_coordinates": gps_coordinates,
            },
        }
    )

    assert request.exif_override == ExifOverrideRequest(
        gps_coordinates=gps_coordinates,
    )


def test_identify_request_rejects_invalid_json_string_payload() -> None:
    with pytest.raises(
        ValidationError,
        match="Invalid JSON string format passed to payload field.",
    ):
        IdentifyRequest.model_validate("{not valid json}")


@pytest.mark.parametrize(
    "gps_coordinates",
    [
        "45.0",
        "north, west",
        "45.0; -93.0",
        "91.0, -93.0",
        "45 61 0 N, 93 0 0 W",
        "45 N, 93 N",
    ],
)
def test_exif_override_rejects_invalid_gps_coordinates(gps_coordinates: str) -> None:
    with pytest.raises(ValidationError):
        ExifOverrideRequest(gps_coordinates=gps_coordinates)


def test_exif_override_rejects_invalid_gps_coordinate_object() -> None:
    with pytest.raises(ValidationError):
        ExifOverrideRequest(gps_coordinates={"latitude": "north", "longitude": -93.0})
