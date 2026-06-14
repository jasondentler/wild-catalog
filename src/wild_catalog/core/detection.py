from dataclasses import dataclass

from wild_catalog.core.bounding_box import BoundingBox


@dataclass(frozen=True, slots=True)
class Detection:
    box: BoundingBox
    confidence: float
    class_id: int
    label: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
