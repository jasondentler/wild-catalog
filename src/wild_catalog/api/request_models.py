from datetime import datetime

from pydantic import BaseModel, Field


class ExifOverrideRequest(BaseModel):
    gps_coordinates: str | None = Field(
        default=None,
        pattern=r"^-?\d+\.\d+,\s*-?\d+\.\d+$",
    )
    captured_at: datetime | None = None


class IdentifyRequest(BaseModel):
    original_filename: str
    exif_override: ExifOverrideRequest | None = None
    return_detected_images: bool = False
    common_name_language: str = "en-US"
