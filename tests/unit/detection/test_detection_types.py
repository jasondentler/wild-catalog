from wild_catalog.core.types import BoundingBox
from wild_catalog.detection.types import Detection, DetectionCategory


def test_detection_type_captures_detector_output() -> None:
    detection = Detection(
        bounding_box=BoundingBox(xmin=0, ymin=1, xmax=2, ymax=3),
        confidence=0.9,
        label="oak",
        category=DetectionCategory.PLANT,
        source="test",
    )

    assert detection.category == DetectionCategory.PLANT
    assert detection.bounding_box.height == 2
