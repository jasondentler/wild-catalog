from contextlib import redirect_stderr
from datetime import datetime
from fractions import Fraction
from io import StringIO
from typing import Any, BinaryIO

import exifread

from wild_catalog.conversion.types import ExtractedMetadata
from wild_catalog.core.types import GpsCoordinates


def extract_metadata(image_file: BinaryIO) -> ExtractedMetadata:
    image_file.seek(0)

    try:
        # exifread can emit low-level parser warnings to stderr for RAW files
        # that are still otherwise readable by the conversion path.
        with redirect_stderr(StringIO()):
            tags = exifread.process_file(image_file, details=False)
    except Exception:
        tags = {}
    finally:
        image_file.seek(0)

    return ExtractedMetadata(
        original_filename=None,
        gps_coordinates=_extract_gps_coordinates(tags),
        captured_at=_extract_captured_at(tags),
    )


def _extract_gps_coordinates(tags: dict[str, Any]) -> GpsCoordinates | None:
    latitude_values = tags.get("GPS GPSLatitude")
    latitude_ref = tags.get("GPS GPSLatitudeRef")
    longitude_values = tags.get("GPS GPSLongitude")
    longitude_ref = tags.get("GPS GPSLongitudeRef")

    if not latitude_values or not latitude_ref or not longitude_values or not longitude_ref:
        return None

    latitude = _dms_to_decimal(latitude_values.values)
    longitude = _dms_to_decimal(longitude_values.values)

    if str(latitude_ref).upper() == "S":
        latitude *= -1

    if str(longitude_ref).upper() == "W":
        longitude *= -1

    return GpsCoordinates(latitude=latitude, longitude=longitude)


def _dms_to_decimal(values: list[Any]) -> float:
    degrees = _ratio_to_float(values[0])
    minutes = _ratio_to_float(values[1])
    seconds = _ratio_to_float(values[2])

    return degrees + minutes / 60 + seconds / 3600


def _ratio_to_float(value: Any) -> float:
    if hasattr(value, "num") and hasattr(value, "den"):
        return float(Fraction(value.num, value.den))

    return float(value)


def _extract_captured_at(tags: dict[str, Any]) -> datetime | None:
    value = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")

    if value is None:
        return None

    try:
        return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
