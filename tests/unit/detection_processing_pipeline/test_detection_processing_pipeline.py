from wild_catalog.core.types import BoundingBox, Detection
from wild_catalog.detection_processing_pipeline.detection_processing_pipeline import (
    DetectionProcessingPipeline,
)


def test_detection_processing_pipeline_maps_detection_without_internal_stages() -> None:
    detection = Detection(
        box=BoundingBox(xmin=1, ymin=2, xmax=11, ymax=22),
        confidence=0.87,
        class_id=3,
        label="animal",
    )

    result = DetectionProcessingPipeline().process(detection)

    assert result.bounding_box == detection.box
    assert result.bounding_box_with_margin == detection.box
    assert result.cropped_image is None
    assert result.predictions[0].confidence == 0.87
    assert result.predictions[0].taxonomy == ("animal",)
    assert result.predictions[0].taxonomy_common_names == ("animal",)
    assert result.predictions[0].class_id == 3


def test_detection_processing_pipeline_maps_missing_label_to_empty_taxonomy() -> None:
    detection = Detection(
        box=BoundingBox(xmin=1, ymin=2, xmax=11, ymax=22),
        confidence=0.87,
        class_id=3,
        label=None,
    )

    result = DetectionProcessingPipeline().process(detection)

    assert result.predictions[0].taxonomy == ()
    assert result.predictions[0].taxonomy_common_names == ()
