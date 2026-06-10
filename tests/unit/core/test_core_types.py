from wild_catalog.core.types import BoundingBox


def test_bounding_box_dimensions() -> None:
    box = BoundingBox(xmin=10, ymin=20, xmax=35, ymax=55)

    assert box.width == 25
    assert box.height == 35
