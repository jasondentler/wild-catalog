from dataclasses import dataclass
from datetime import datetime

from PIL import Image

from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.taxonomy.types import EnrichedPrediction


@dataclass(frozen=True, slots=True)
class ExifOverride:
    gps_coordinates: GpsCoordinates | None = None
    captured_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class IdentifyCommand:
    original_filename: str
    exif_override: ExifOverride | None = None
    return_detected_images: bool = False
    common_name_language: str = "en-US"


@dataclass(frozen=True, slots=True)
class IdentifiedObject:
    bounding_box: BoundingBox
    bounding_box_with_margin: BoundingBox
    gps_coordinates: GpsCoordinates | None
    predictions: tuple[EnrichedPrediction, ...]
    cropped_image: Image.Image | None = None


@dataclass(frozen=True, slots=True)
class IdentifyResult:
    objects: tuple[IdentifiedObject, ...]
