from dataclasses import dataclass

from PIL import Image

from wild_catalog.core.types import BoundingBox
from wild_catalog.detection.types import Detection


@dataclass(frozen=True, slots=True)
class CropResult:
    index: int
    detection: Detection
    bounding_box: BoundingBox
    bounding_box_with_margin: BoundingBox
    image: Image.Image
