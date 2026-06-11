import json
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ExifOverrideRequest(BaseModel):
    gps_coordinates: str | None = Field(
        default=None,
        pattern=r"^-?\d+\.\d+,\s*-?\d+\.\d+$",
        examples=["29.573361, -94.389507"],
    )
    captured_at: datetime | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "gps_coordinates": "29.573361, -94.389507",
                    "captured_at": "2026-05-01T12:30:00Z",
                }
            ]
        }
    }


class IdentifyRequest(BaseModel):
    original_filename: str = Field(default=None, examples=["IMG_7906.jpg"])
    exif_override: ExifOverrideRequest | None = None
    return_detected_images: bool = False
    common_name_language: str = "en-US"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "original_filename": "IMG_7906.jpg",
                    "exif_override": {
                        "gps_coordinates": "29.573361, -94.389507",
                        "captured_at": "2026-05-01T12:30:00Z",
                    },
                    "return_detected_images": True,
                    "common_name_language": "en-US",
                }
            ]
        }
    }

    @model_validator(mode="before")
    @classmethod
    def validate_to_json(cls, value):
        # If FastAPI passes the form field as a raw string, parse it into a dict
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string format passed to payload field.")  # noqa: B904
        return value
