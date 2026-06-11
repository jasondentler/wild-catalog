
from dataclasses import dataclass

from PIL import Image

from wild_catalog.core.types import BoundingBox, GpsCoordinates


@dataclass(frozen=True, slots=True)
class Prediction:
    confidence: float = 0.0
    is_present: bool = False
    taxonomy: tuple[str, ...] = ()
    taxonomy_common_names: tuple[str, ...] = ()
    class_id: int = -1
    taxon_id: int = -1
    accepted_taxon_id: int = -1
    taxonomy_rank_names: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class IdentifiedObject:
    bounding_box: BoundingBox
    bounding_box_with_margin: BoundingBox
    gps_coordinates: GpsCoordinates | None
    predictions: tuple[Prediction, ...]
    cropped_image: Image.Image | None = None


@dataclass(frozen=True, slots=True)
class IdentifyResult:
    objects: tuple[IdentifiedObject, ...]
    return_detected_images: bool = False
