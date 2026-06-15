from dataclasses import dataclass

from PIL import Image

from wild_catalog.core.bounding_box import BoundingBox


@dataclass(frozen=True, slots=True)
class CropResult:
    original_box: BoundingBox
    box_with_margin: BoundingBox
    cropped_image: Image.Image
