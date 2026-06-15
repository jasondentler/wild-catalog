from wild_catalog.core.types import BoundingBox, Detection
from wild_catalog.deduplicate_detections.detection_deduplicator import DetectionDeduplicator


def test_calculate_iou_returns_zero_when_boxes_do_not_overlap() -> None:
    assert (
        DetectionDeduplicator.calculate_iou(
            BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10),
            BoundingBox(xmin=20, ymin=20, xmax=30, ymax=30),
        )
        == 0.0
    )


def test_calculate_iou_returns_intersection_over_union() -> None:
    assert DetectionDeduplicator.calculate_iou(
        BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10),
        BoundingBox(xmin=5, ymin=5, xmax=15, ymax=15),
    ) == 25 / 175


def test_detection_deduplicator_keeps_highest_confidence_duplicate() -> None:
    low_confidence = Detection(
        box=BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10),
        confidence=0.4,
        class_id=0,
        label="animal",
    )
    high_confidence = Detection(
        box=BoundingBox(xmin=1, ymin=1, xmax=11, ymax=11),
        confidence=0.9,
        class_id=0,
        label="animal",
    )

    assert DetectionDeduplicator().deduplicate([low_confidence, high_confidence]) == [
        high_confidence
    ]


def test_detection_deduplicator_matches_normalized_labels() -> None:
    first = Detection(
        box=BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10),
        confidence=0.9,
        class_id=1,
        label=" Animal ",
    )
    second = Detection(
        box=BoundingBox(xmin=1, ymin=1, xmax=11, ymax=11),
        confidence=0.8,
        class_id=2,
        label="animal",
    )

    assert DetectionDeduplicator().deduplicate([first, second]) == [first]


def test_detection_deduplicator_keeps_distinct_classes_and_empty_labels() -> None:
    first = Detection(
        box=BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10),
        confidence=0.9,
        class_id=1,
        label=None,
    )
    second = Detection(
        box=BoundingBox(xmin=1, ymin=1, xmax=11, ymax=11),
        confidence=0.8,
        class_id=2,
        label="  ",
    )

    assert DetectionDeduplicator().deduplicate([first, second]) == [first, second]


def test_detection_deduplicator_filters_overlapping_boxes_with_configured_threshold() -> None:
    first = Detection(
        box=BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10),
        confidence=0.9,
        class_id=0,
        label="animal",
    )
    second = Detection(
        box=BoundingBox(xmin=5, ymin=5, xmax=15, ymax=15),
        confidence=0.8,
        class_id=0,
        label="animal",
    )

    assert DetectionDeduplicator(iou_threshold=0.1).deduplicate([first, second]) == [first]
