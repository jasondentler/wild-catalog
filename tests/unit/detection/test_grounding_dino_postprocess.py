from wild_catalog.core.types import BoundingBox
from wild_catalog.detection.grounding_dino_postprocess import (
    GroundingDinoPrediction,
    detection_category_for_label,
    normalize_detection_label,
    normalized_cxcywh_to_bounding_box,
    postprocess_grounding_dino_predictions,
    xyxy_to_bounding_box,
)
from wild_catalog.detection.types import DetectionCategory


def test_normalize_detection_label() -> None:
    assert normalize_detection_label("  Bird. ") == "bird"
    assert normalize_detection_label("Small   Mammal!") == "small mammal"


def test_detection_category_for_label_maps_supported_labels() -> None:
    assert detection_category_for_label("small bird") is DetectionCategory.ANIMAL
    assert detection_category_for_label("green leaf") is DetectionCategory.PLANT
    assert detection_category_for_label("mushroom") is DetectionCategory.FUNGUS
    assert detection_category_for_label("lichen") is DetectionCategory.LICHEN
    assert detection_category_for_label("rock") is None


def test_normalized_cxcywh_to_pixel_bounding_box() -> None:
    bounding_box = normalized_cxcywh_to_bounding_box(
        (0.5, 0.5, 0.4, 0.2),
        image_width=200,
        image_height=100,
    )

    assert bounding_box == BoundingBox(xmin=60, ymin=40, xmax=140, ymax=60)


def test_xyxy_to_bounding_box_clamps_to_image_bounds() -> None:
    bounding_box = xyxy_to_bounding_box(
        (-10.0, 5.0, 250.0, 120.0),
        image_width=200,
        image_height=100,
    )

    assert bounding_box == BoundingBox(xmin=0, ymin=5, xmax=200, ymax=100)


def test_xyxy_to_bounding_box_drops_invalid_boxes() -> None:
    assert (
        xyxy_to_bounding_box(
            (10.0, 10.0, 10.0, 20.0),
            image_width=200,
            image_height=100,
        )
        is None
    )


def test_postprocess_filters_and_sorts_detections() -> None:
    detections = postprocess_grounding_dino_predictions(
        (
            GroundingDinoPrediction(box=(0, 0, 50, 50), score=0.7, label="bird."),
            GroundingDinoPrediction(box=(0, 0, 50, 50), score=0.2, label="mammal"),
            GroundingDinoPrediction(box=(0, 0, 50, 50), score=0.9, label="flower"),
            GroundingDinoPrediction(box=(10, 10, 10, 50), score=0.95, label="animal"),
            GroundingDinoPrediction(box=(0, 0, 50, 50), score=0.8, label="chair"),
        ),
        image_width=100,
        image_height=100,
        confidence_threshold=0.25,
        boxes_are_normalized_cxcywh=False,
    )

    assert [detection.confidence for detection in detections] == [0.9, 0.7]
    assert [detection.category for detection in detections] == [
        DetectionCategory.PLANT,
        DetectionCategory.ANIMAL,
    ]
    assert [detection.label for detection in detections] == ["flower", "bird"]
