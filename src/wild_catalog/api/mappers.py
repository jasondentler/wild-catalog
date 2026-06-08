from wild_catalog.api.request_models import IdentifyRequest
from wild_catalog.core.errors import InvalidGpsOverrideError
from wild_catalog.core.types import GpsCoordinates
from wild_catalog.pipeline.models import ExifOverride, IdentifyCommand


def parse_gps_coordinates(value: str) -> GpsCoordinates:
    try:
        latitude_text, longitude_text = value.split(",", maxsplit=1)
        coordinates = GpsCoordinates(
            latitude=float(latitude_text.strip()),
            longitude=float(longitude_text.strip()),
        )
    except ValueError as exc:
        raise InvalidGpsOverrideError(
            public_detail="Invalid GPS override.",
            debug_detail=f"Unable to parse GPS override: {value!r}",
        ) from exc

    if not -90 <= coordinates.latitude <= 90 or not -180 <= coordinates.longitude <= 180:
        raise InvalidGpsOverrideError(
            public_detail="Invalid GPS override.",
            debug_detail=f"GPS override is outside valid bounds: {value!r}",
        )

    return coordinates


def identify_request_to_command(request: IdentifyRequest) -> IdentifyCommand:
    exif_override = None

    if request.exif_override is not None:
        gps_coordinates = (
            parse_gps_coordinates(request.exif_override.gps_coordinates)
            if request.exif_override.gps_coordinates is not None
            else None
        )

        exif_override = ExifOverride(
            gps_coordinates=gps_coordinates,
            captured_at=request.exif_override.captured_at,
        )

    return IdentifyCommand(
        original_filename=request.original_filename,
        exif_override=exif_override,
        return_detected_images=request.return_detected_images,
        common_name_language=request.common_name_language,
    )
