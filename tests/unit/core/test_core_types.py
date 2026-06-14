import pytest

from wild_catalog.core.types import BoundingBox, Detection


def test_bounding_box_dimensions() -> None:
    box = BoundingBox(xmin=10, ymin=20, xmax=35, ymax=55)

    assert box.width == 25
    assert box.height == 35


def test_detection_rejects_confidence_outside_probability_range() -> None:
    with pytest.raises(ValueError, match="confidence"):
        Detection(
            box=BoundingBox(xmin=0, ymin=0, xmax=1, ymax=1),
            confidence=1.1,
            class_id=0,
        )
