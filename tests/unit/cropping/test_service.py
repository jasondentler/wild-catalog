from PIL import Image

from wild_catalog.core.types import BoundingBox
from wild_catalog.cropping.service import ImageCropper
from wild_catalog.detection.types import Detection, DetectionCategory


def make_detection(box: BoundingBox) -> Detection:
    return Detection(
        bounding_box=box,
        confidence=0.9,
        label="bird",
        category=DetectionCategory.ANIMAL,
        source="test",
    )


def test_extract_target_regions_returns_ordered_crop_results() -> None:
    image = Image.new("RGB", (100, 80), color=(255, 255, 255))
    detections = [
        make_detection(BoundingBox(xmin=20, ymin=10, xmax=40, ymax=30)),
        make_detection(BoundingBox(xmin=50, ymin=40, xmax=70, ymax=60)),
    ]

    results = ImageCropper(margin_ratio=0.25).extract_target_regions(image, detections)

    assert [result.index for result in results] == [0, 1]
    assert [result.detection for result in results] == detections
    assert results[0].bounding_box == detections[0].bounding_box
    assert results[0].bounding_box_with_margin == BoundingBox(
        xmin=15,
        ymin=5,
        xmax=45,
        ymax=35,
    )
    assert results[0].image.mode == "RGB"
    assert results[0].image.size == (30, 30)
    assert results[1].bounding_box_with_margin == BoundingBox(
        xmin=45,
        ymin=35,
        xmax=75,
        ymax=65,
    )
    assert results[1].image.size == (30, 30)


def test_extract_target_regions_returns_empty_list_without_detections() -> None:
    image = Image.new("RGB", (100, 80), color=(255, 255, 255))

    results = ImageCropper(margin_ratio=0.25).extract_target_regions(image, [])

    assert results == []
