import pytest

from wild_catalog.core.types import BoundingBox
from wild_catalog.deduplication.service import DetectionDeduplicator
from wild_catalog.detection.types import Detection, DetectionCategory


def test_filter_overlapping_detections_returns_empty_list_for_empty_input() -> None:
    deduplicator = DetectionDeduplicator()

    assert deduplicator.filter_overlapping_detections([]) == []


def test_filter_overlapping_detections_keeps_non_overlapping_same_category() -> None:
    deduplicator = DetectionDeduplicator(iou_threshold=0.45)

    detections = [
        make_detection(
            xmin=0,
            ymin=0,
            xmax=10,
            ymax=10,
            confidence=0.9,
            label="bird",
            category=DetectionCategory.ANIMAL,
        ),
        make_detection(
            xmin=20,
            ymin=20,
            xmax=30,
            ymax=30,
            confidence=0.8,
            label="animal",
            category=DetectionCategory.ANIMAL,
        ),
    ]

    result = deduplicator.filter_overlapping_detections(detections)

    assert result == detections


def test_filter_overlapping_detections_drops_lower_confidence_same_category_overlap() -> None:
    deduplicator = DetectionDeduplicator(iou_threshold=0.45)

    higher_confidence = make_detection(
        xmin=0,
        ymin=0,
        xmax=20,
        ymax=20,
        confidence=0.9,
        label="bird",
        category=DetectionCategory.ANIMAL,
    )
    lower_confidence = make_detection(
        xmin=1,
        ymin=1,
        xmax=21,
        ymax=21,
        confidence=0.8,
        label="animal",
        category=DetectionCategory.ANIMAL,
    )

    result = deduplicator.filter_overlapping_detections(
        [
            lower_confidence,
            higher_confidence,
        ]
    )

    assert result == [higher_confidence]


def test_filter_overlapping_detections_keeps_overlapping_different_categories() -> None:
    deduplicator = DetectionDeduplicator(iou_threshold=0.45)

    animal = make_detection(
        xmin=0,
        ymin=0,
        xmax=20,
        ymax=20,
        confidence=0.9,
        label="bird",
        category=DetectionCategory.ANIMAL,
    )
    plant = make_detection(
        xmin=1,
        ymin=1,
        xmax=21,
        ymax=21,
        confidence=0.8,
        label="plant",
        category=DetectionCategory.PLANT,
    )

    result = deduplicator.filter_overlapping_detections(
        [
            plant,
            animal,
        ]
    )

    assert result == [animal, plant]


def test_filter_overlapping_detections_dedupes_broad_and_specific_same_category_labels() -> None:
    deduplicator = DetectionDeduplicator(iou_threshold=0.45)

    bird = make_detection(
        xmin=0,
        ymin=0,
        xmax=20,
        ymax=20,
        confidence=0.88,
        label="bird",
        category=DetectionCategory.ANIMAL,
    )
    animal = make_detection(
        xmin=1,
        ymin=1,
        xmax=21,
        ymax=21,
        confidence=0.90,
        label="animal",
        category=DetectionCategory.ANIMAL,
    )

    result = deduplicator.filter_overlapping_detections(
        [
            bird,
            animal,
        ]
    )

    assert result == [animal]


def test_filter_overlapping_detections_keeps_detection_when_iou_equals_threshold() -> None:
    deduplicator = DetectionDeduplicator(iou_threshold=0.5)

    first = make_detection(
        xmin=0,
        ymin=0,
        xmax=10,
        ymax=10,
        confidence=0.9,
        label="bird",
        category=DetectionCategory.ANIMAL,
    )
    second = make_detection(
        xmin=0,
        ymin=0,
        xmax=10,
        ymax=5,
        confidence=0.8,
        label="animal",
        category=DetectionCategory.ANIMAL,
    )

    result = deduplicator.filter_overlapping_detections(
        [
            first,
            second,
        ]
    )

    assert result == [first, second]


def test_detection_deduplicator_rejects_negative_threshold() -> None:
    with pytest.raises(ValueError, match="iou_threshold"):
        DetectionDeduplicator(iou_threshold=-0.1)


def test_detection_deduplicator_rejects_threshold_above_one() -> None:
    with pytest.raises(ValueError, match="iou_threshold"):
        DetectionDeduplicator(iou_threshold=1.1)


def test_filter_overlapping_detections_returns_kept_items_in_confidence_order() -> None:
    deduplicator = DetectionDeduplicator(iou_threshold=0.45)

    low = make_detection(
        xmin=40,
        ymin=40,
        xmax=50,
        ymax=50,
        confidence=0.1,
        label="bird",
        category=DetectionCategory.ANIMAL,
    )
    high = make_detection(
        xmin=0,
        ymin=0,
        xmax=10,
        ymax=10,
        confidence=0.9,
        label="bird",
        category=DetectionCategory.ANIMAL,
    )
    medium = make_detection(
        xmin=20,
        ymin=20,
        xmax=30,
        ymax=30,
        confidence=0.5,
        label="bird",
        category=DetectionCategory.ANIMAL,
    )

    result = deduplicator.filter_overlapping_detections(
        [
            low,
            high,
            medium,
        ]
    )

    assert result == [high, medium, low]


def test_deduplicate_removes_overlapping_grounding_dino_boxes_from_cormorant_fixture() -> None:
    detections = [
        make_detection_with_box(BoundingBox(331, 417, 1548, 1632), confidence=0.92),
        make_detection_with_box(BoundingBox(11, 7, 2038, 1632), confidence=0.80),
        make_detection_with_box(BoundingBox(333, 417, 1550, 1633), confidence=0.91),
        make_detection_with_box(BoundingBox(331, 417, 1551, 1633), confidence=0.90),
        make_detection_with_box(BoundingBox(332, 417, 1548, 1632), confidence=0.89),
        make_detection_with_box(BoundingBox(331, 418, 1551, 1633), confidence=0.88),
        make_detection_with_box(BoundingBox(332, 418, 1550, 1633), confidence=0.87),
        make_detection_with_box(BoundingBox(331, 417, 1551, 1633), confidence=0.86),
    ]

    deduplicated = DetectionDeduplicator(iou_threshold=0.45).filter_overlapping_detections(
        detections
    )

    assert [detection.bounding_box for detection in deduplicated] == [
        BoundingBox(331, 417, 1548, 1632),
        BoundingBox(11, 7, 2038, 1632),
    ]


def make_detection(
    *,
    xmin: int,
    ymin: int,
    xmax: int,
    ymax: int,
    confidence: float,
    label: str,
    category: DetectionCategory,
) -> Detection:
    return Detection(
        bounding_box=BoundingBox(
            xmin=xmin,
            ymin=ymin,
            xmax=xmax,
            ymax=ymax,
        ),
        confidence=confidence,
        label=label,
        category=category,
        source="test",
    )


def make_detection_with_box(bounding_box: BoundingBox, *, confidence: float) -> Detection:
    return Detection(
        bounding_box=bounding_box,
        confidence=confidence,
        label="bird",
        category=DetectionCategory.ANIMAL,
        source="grounding-dino",
    )
