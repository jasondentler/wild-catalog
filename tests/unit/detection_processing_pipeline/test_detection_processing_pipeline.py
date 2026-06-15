from PIL import Image

from wild_catalog.core.settings import Settings
from wild_catalog.core.types import BoundingBox, Detection
from wild_catalog.detection_processing_pipeline.detection_processing_pipeline import (
    DetectionProcessingPipeline,
)
from wild_catalog.image_cropper.image_cropping import ImageCropper


def test_detection_processing_pipeline_maps_detection_without_internal_stages() -> None:
    image = Image.new("RGB", (100, 120), color=(255, 0, 0))
    detection = Detection(
        box=BoundingBox(xmin=1, ymin=2, xmax=11, ymax=22),
        confidence=0.87,
        class_id=3,
        label="animal",
    )

    result = DetectionProcessingPipeline(
        ImageCropper(
            Settings(
                crop_margin_ratio=0.1,
                crop_margin_min_px=8,
            )
        )
    ).process(image, detection)

    assert result.bounding_box == detection.box
    assert result.bounding_box_with_margin == BoundingBox(
        xmin=0,
        ymin=0,
        xmax=19,
        ymax=30,
    )
    assert result.cropped_image.size == (19, 30)
    assert result.predictions[0].confidence == 0.87
    assert result.predictions[0].taxonomy == ("animal",)
    assert result.predictions[0].taxonomy_common_names == ("animal",)
    assert result.predictions[0].class_id == 3


def test_detection_processing_pipeline_maps_missing_label_to_empty_taxonomy() -> None:
    image = Image.new("RGB", (100, 120), color=(255, 0, 0))
    detection = Detection(
        box=BoundingBox(xmin=1, ymin=2, xmax=11, ymax=22),
        confidence=0.87,
        class_id=3,
        label=None,
    )

    result = DetectionProcessingPipeline(
        ImageCropper(
            Settings(
                crop_margin_ratio=0.1,
                crop_margin_min_px=8,
            )
        )
    ).process(image, detection)

    assert result.predictions[0].taxonomy == ()
    assert result.predictions[0].taxonomy_common_names == ()
