import json
import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

GpsCoordinatesString = Annotated[
    str,
    Field(
        examples=[
            "29.573361, -94.389507",
            '29°34\'24.1"N, 94°23\'22.2"W',
        ],
    ),
]


class GpsCoordinatesRequest(BaseModel):
    latitude: float
    longitude: float


class ExifOverrideRequest(BaseModel):
    gps_coordinates: GpsCoordinatesRequest | GpsCoordinatesString | None = Field(
        default=None,
        examples=[
            {"latitude": 29.573361, "longitude": -94.389507},
            "29.573361, -94.389507",
        ],
    )
    captured_at: datetime | None = None

    @field_validator("gps_coordinates")
    @classmethod
    def validate_gps_coordinates(
        cls,
        value: GpsCoordinatesRequest | str | None,
    ) -> GpsCoordinatesRequest | str | None:
        if isinstance(value, str):
            parse_gps_coordinate_string(value)

        return value

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "gps_coordinates": {
                        "latitude": 29.573361,
                        "longitude": -94.389507,
                    },
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
                        "gps_coordinates": {
                            "latitude": 29.573361,
                            "longitude": -94.389507,
                        },
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


def parse_gps_coordinate_string(value: str) -> tuple[float, float]:
    parts = _split_gps_coordinate_string(value)

    if len(parts) != 2:
        raise ValueError("GPS coordinates must contain latitude and longitude.")

    latitude = _parse_gps_coordinate_part(parts[0], axis="latitude")
    longitude = _parse_gps_coordinate_part(parts[1], axis="longitude")

    return latitude, longitude


def _split_gps_coordinate_string(value: str) -> tuple[str, str]:
    stripped_value = value.strip()

    if "," in stripped_value:
        parts = [part.strip() for part in stripped_value.split(",")]

        if len(parts) == 2 and all(parts):
            return parts[0], parts[1]

        raise ValueError("GPS coordinates must contain latitude and longitude.")

    cardinal_parts = _split_gps_coordinate_string_by_cardinal_direction(stripped_value)

    if cardinal_parts is not None:
        return cardinal_parts

    if ";" in stripped_value:
        raise ValueError("GPS coordinates must contain latitude and longitude.")

    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", stripped_value)

    if len(numbers) not in {2, 4, 6}:
        raise ValueError("GPS coordinates must contain latitude and longitude.")

    midpoint = len(numbers) // 2
    return " ".join(numbers[:midpoint]), " ".join(numbers[midpoint:])


def _split_gps_coordinate_string_by_cardinal_direction(
    value: str,
) -> tuple[str, str] | None:
    directions = list(re.finditer(r"[NSEW]", value.upper()))

    if not directions:
        return None

    if len(directions) != 2:
        raise ValueError("GPS coordinates must contain one latitude and one longitude.")

    first_direction, second_direction = directions
    first_number = re.search(r"[-+]?\d+(?:\.\d+)?", value)

    if first_number is None:
        raise ValueError("GPS coordinates must contain degrees.")

    if first_direction.start() < first_number.start():
        first_part = value[: second_direction.start()].strip()
        second_part = value[second_direction.start() :].strip()
    else:
        first_part = value[: first_direction.end()].strip()
        second_part = value[first_direction.end() :].strip()

    first_axis = _axis_for_gps_coordinate_part(first_part)
    second_axis = _axis_for_gps_coordinate_part(second_part)

    if first_axis == "latitude" and second_axis == "longitude":
        return first_part, second_part

    if first_axis == "longitude" and second_axis == "latitude":
        return second_part, first_part

    raise ValueError("GPS coordinates must contain one latitude and one longitude.")


def _axis_for_gps_coordinate_part(value: str) -> str | None:
    cardinal_directions = set(re.findall(r"[NSEW]", value.upper()))

    if cardinal_directions & {"N", "S"}:
        return "latitude"

    if cardinal_directions & {"E", "W"}:
        return "longitude"

    return None


def _parse_gps_coordinate_part(value: str, *, axis: str) -> float:
    cardinal_directions = re.findall(r"[NSEW]", value.upper())

    if len(cardinal_directions) > 1:
        raise ValueError("GPS coordinate contains too many cardinal directions.")

    numbers = [float(number) for number in re.findall(r"[-+]?\d+(?:\.\d+)?", value)]

    if not 1 <= len(numbers) <= 3:
        raise ValueError("GPS coordinate must contain degrees, minutes, and seconds.")

    degrees = numbers[0]
    minutes = numbers[1] if len(numbers) >= 2 else 0.0
    seconds = numbers[2] if len(numbers) == 3 else 0.0

    if not 0 <= minutes < 60:
        raise ValueError("GPS coordinate minutes must be from 0 to less than 60.")

    if not 0 <= seconds < 60:
        raise ValueError("GPS coordinate seconds must be from 0 to less than 60.")

    sign = -1.0 if degrees < 0 else 1.0

    if cardinal_directions:
        direction = cardinal_directions[0]
        _validate_cardinal_direction(direction, axis=axis)
        sign = -1.0 if direction in {"S", "W"} else 1.0

    decimal_degrees = abs(degrees) + minutes / 60.0 + seconds / 3600.0
    result = sign * decimal_degrees
    limit = 90.0 if axis == "latitude" else 180.0

    if abs(result) > limit:
        raise ValueError(f"GPS coordinate {axis} is outside the valid range.")

    return result


def _validate_cardinal_direction(direction: str, *, axis: str) -> None:
    valid_directions = {"N", "S"} if axis == "latitude" else {"E", "W"}

    if direction not in valid_directions:
        raise ValueError(f"GPS coordinate contains invalid {axis} direction.")
