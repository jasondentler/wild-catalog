from dataclasses import dataclass
from datetime import datetime

from PIL import Image

from wild_catalog.core.types import GpsCoordinates


@dataclass(frozen=True, slots=True)
class ExtractedMetadata:
    original_filename: str | None = None
    gps_coordinates: GpsCoordinates | None = None
    captured_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ConvertedImage:
    image: Image.Image
    original_filename: str
    gps_coordinates: GpsCoordinates | None
    captured_at: datetime | None
    detected_format: str
