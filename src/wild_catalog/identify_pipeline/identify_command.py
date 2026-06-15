
from dataclasses import dataclass
from datetime import datetime

from wild_catalog.core.types import GpsCoordinates


@dataclass(frozen=True, slots=True)
class ExifOverride:
    gps_coordinates: GpsCoordinates | None = None
    captured_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class IdentifyCommand:
    original_filename: str | None = None
    image_size_bytes: int | None = None
    exif_override: ExifOverride | None = None
    return_detected_images: bool = False
    common_name_language: str = "en-US"

    @classmethod
    def create(cls, **kwargs):
        # Strip out any keys where the user explicitly passed None
        # This forces the dataclass to use its built-in defaults
        filtered_kwargs = {k: v for k, v in kwargs.items() if v is not None}
        return cls(**filtered_kwargs)
