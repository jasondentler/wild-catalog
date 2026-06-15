from PIL import Image

from wild_catalog.core.settings import Settings
from wild_catalog.core.types import BoundingBox, Detection
from wild_catalog.detection_processing_pipeline.detection_processing_pipeline import (
    DetectionProcessingPipeline,
)
from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.image_cropper.image_cropping import ImageCropper


class _Classifier:
    def __init__(self, predictions: list[Prediction]) -> None:
        self.predictions = predictions
        self.calls = []

    def classify(self, image: Image.Image) -> list[Prediction]:
        self.calls.append(image)
        return self.predictions


def test_detection_processing_pipeline_crops_detection_and_classifies_crop() -> None:
    image = Image.new("RGB", (100, 120), color=(255, 0, 0))
    detection = Detection(
        box=BoundingBox(xmin=1, ymin=2, xmax=11, ymax=22),
        confidence=0.87,
        class_id=3,
        label="animal",
    )
    classifier = _Classifier(
        [
            Prediction(
                confidence=0.72,
                is_present=True,
                taxonomy=("mallard",),
                taxonomy_common_names=("mallard",),
                class_id=17,
            )
        ]
    )

    result = DetectionProcessingPipeline(
        ImageCropper(
            Settings(
                crop_margin_ratio=0.1,
                crop_margin_min_px=8,
            )
        ),
        classifier,
    ).process(image, detection)

    assert result.bounding_box == detection.box
    assert result.bounding_box_with_margin == BoundingBox(
        xmin=0,
        ymin=0,
        xmax=19,
        ymax=30,
    )
    assert result.cropped_image.size == (19, 30)
    assert classifier.calls == [result.cropped_image]
    assert result.predictions == tuple(classifier.predictions)


def test_detection_processing_pipeline_returns_empty_predictions_when_classifier_has_none() -> None:
    image = Image.new("RGB", (100, 120), color=(255, 0, 0))
    detection = Detection(
        box=BoundingBox(xmin=1, ymin=2, xmax=11, ymax=22),
        confidence=0.87,
        class_id=3,
        label=None,
    )
    classifier = _Classifier([])

    result = DetectionProcessingPipeline(
        ImageCropper(
            Settings(
                crop_margin_ratio=0.1,
                crop_margin_min_px=8,
            )
        ),
        classifier,
    ).process(image, detection)

    assert result.predictions == ()
