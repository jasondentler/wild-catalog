from dataclasses import dataclass

from wild_catalog.core.types import GpsCoordinates
from wild_catalog.pipeline.identified_object import IdentifiedObject
from wild_catalog.pipeline.prediction import Prediction


@dataclass(frozen=True, slots=True)
class IdentifyResult:
    objects: tuple[IdentifiedObject, ...]
    gps_coordinates: GpsCoordinates | None = None
    return_detected_images: bool = False


__all__ = ["IdentifiedObject", "IdentifyResult", "Prediction"]
