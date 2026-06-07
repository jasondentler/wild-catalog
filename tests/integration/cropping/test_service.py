import os

import pytest
from PIL import Image

from wild_catalog.core.types import BoundingBox
from wild_catalog.cropping.service import ImageCropper
from wild_catalog.detection.types import Detection, DetectionCategory

pytestmark = pytest.mark.integration

requires_enabled_integration_suite = pytest.mark.skipif(
    os.getenv("WILD_CATALOG_RUN_INTEGRATION_TESTS") != "1",
    reason="Skipping integration test suite. Run 'make test' to execute.",
)


def make_detection(box: BoundingBox) -> Detection:
    return Detection(
        bounding_box=box,
        confidence=0.95,
        label="edge subject",
        category=DetectionCategory.UNKNOWN,
        source="test",
    )


@requires_enabled_integration_suite
@pytest.mark.parametrize(
    ("box", "expected_box", "expected_size"),
    [
        (
            BoundingBox(xmin=2, ymin=3, xmax=22, ymax=23),
            BoundingBox(xmin=0, ymin=0, xmax=32, ymax=33),
            (32, 33),
        ),
        (
            BoundingBox(xmin=78, ymin=57, xmax=98, ymax=77),
            BoundingBox(xmin=68, ymin=47, xmax=100, ymax=80),
            (32, 33),
        ),
    ],
)
def test_extract_target_regions_clamps_margin_that_exceeds_image_bounds(
    box: BoundingBox,
    expected_box: BoundingBox,
    expected_size: tuple[int, int],
) -> None:
    image = Image.new("RGB", (100, 80), color=(12, 34, 56))
    detection = make_detection(box)

    crop = ImageCropper(margin_ratio=0.5).extract_target_regions(image, [detection])[0]

    assert crop.bounding_box == box
    assert crop.bounding_box_with_margin == expected_box
    assert crop.image.mode == "RGB"
    assert crop.image.size == expected_size
    assert crop.image.getpixel((0, 0)) == (12, 34, 56)
