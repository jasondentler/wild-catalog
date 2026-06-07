from wild_catalog.core.types import BoundingBox
from wild_catalog.detection.types import Detection, DetectionCategory


def test_detection_stores_normalized_detector_output() -> None:
    detection = Detection(
        bounding_box=BoundingBox(xmin=1, ymin=2, xmax=3, ymax=4),
        confidence=0.9,
        label="bird",
        category=DetectionCategory.ANIMAL,
        source="grounding-dino",
    )

    assert detection.label == "bird"
    assert detection.category == DetectionCategory.ANIMAL
    assert detection.source == "grounding-dino"
