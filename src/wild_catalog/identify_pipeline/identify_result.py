from dataclasses import dataclass
from datetime import datetime

from wild_catalog.core.types import GpsCoordinates
from wild_catalog.identify_pipeline.identified_object import IdentifiedObject
from wild_catalog.identify_pipeline.prediction import Prediction


@dataclass(frozen=True, slots=True)
class IdentifyResult:
    objects: tuple[IdentifiedObject, ...]
    original_filename: str | None = None
    captured_at: datetime | None = None
    gps_coordinates: GpsCoordinates | None = None
    return_detected_images: bool = False


__all__ = ["IdentifiedObject", "IdentifyResult", "Prediction"]
