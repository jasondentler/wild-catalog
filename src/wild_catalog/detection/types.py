from dataclasses import dataclass
from enum import StrEnum

from wild_catalog.core.types import BoundingBox


class DetectionCategory(StrEnum):
    ANIMAL = "animal"
    PLANT = "plant"
    FUNGUS = "fungus"
    LICHEN = "lichen"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class Detection:
    bounding_box: BoundingBox
    confidence: float
    label: str
    category: DetectionCategory
    source: str
