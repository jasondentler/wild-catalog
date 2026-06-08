import pytest

from wild_catalog.core.types import BoundingBox
from wild_catalog.deduplication.iou import calculate_iou


def test_calculate_iou_returns_zero_for_non_overlapping_boxes() -> None:
    a = BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10)
    b = BoundingBox(xmin=20, ymin=20, xmax=30, ymax=30)

    assert calculate_iou(a, b) == 0.0


def test_calculate_iou_returns_zero_for_edge_touching_boxes() -> None:
    a = BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10)
    b = BoundingBox(xmin=10, ymin=0, xmax=20, ymax=10)

    assert calculate_iou(a, b) == 0.0


def test_calculate_iou_returns_one_for_identical_boxes() -> None:
    box = BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10)

    assert calculate_iou(box, box) == 1.0


def test_calculate_iou_returns_expected_overlap_ratio() -> None:
    a = BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10)
    b = BoundingBox(xmin=5, ymin=5, xmax=15, ymax=15)

    assert calculate_iou(a, b) == pytest.approx(25 / 175)


def test_calculate_iou_is_symmetric() -> None:
    a = BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10)
    b = BoundingBox(xmin=5, ymin=5, xmax=15, ymax=15)

    assert calculate_iou(a, b) == calculate_iou(b, a)


def test_calculate_iou_returns_zero_for_zero_area_box() -> None:
    a = BoundingBox(xmin=0, ymin=0, xmax=0, ymax=10)
    b = BoundingBox(xmin=0, ymin=0, xmax=10, ymax=10)

    assert calculate_iou(a, b) == 0.0
