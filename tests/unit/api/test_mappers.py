from datetime import UTC, datetime

from wild_catalog.api.mappers import identify_request_to_command, parse_gps_coordinates
from wild_catalog.api.request_models import ExifOverrideRequest, IdentifyRequest
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.pipeline.models import ExifOverride, IdentifyCommand


def test_parse_gps_coordinates_returns_domain_type() -> None:
    assert parse_gps_coordinates("29.7604, -95.3698") == GpsCoordinates(
        latitude=29.7604,
        longitude=-95.3698,
    )


def test_identify_request_to_command_maps_api_request_to_pipeline_command() -> None:
    captured_at = datetime(2026, 5, 1, 12, 30, tzinfo=UTC)

    assert identify_request_to_command(
        IdentifyRequest(
            original_filename="image.jpg",
            exif_override=ExifOverrideRequest(
                gps_coordinates="29.7604, -95.3698",
                captured_at=captured_at,
            ),
            return_detected_images=True,
            common_name_language="es-MX",
        )
    ) == IdentifyCommand(
        original_filename="image.jpg",
        exif_override=ExifOverride(
            gps_coordinates=GpsCoordinates(latitude=29.7604, longitude=-95.3698),
            captured_at=captured_at,
        ),
        return_detected_images=True,
        common_name_language="es-MX",
    )
