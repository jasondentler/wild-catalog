from dataclasses import dataclass

from PIL import Image

from wild_catalog.core.types import BoundingBox
from wild_catalog.pipeline.prediction import Prediction


@dataclass(frozen=True, slots=True)
class IdentifiedObject:
    bounding_box: BoundingBox
    bounding_box_with_margin: BoundingBox
    predictions: tuple[Prediction, ...]
    cropped_image: Image.Image | None = None
