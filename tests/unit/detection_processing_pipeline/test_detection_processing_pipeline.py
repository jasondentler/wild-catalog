from dataclasses import replace

import pytest
import torch
from PIL import Image

from wild_catalog.core.settings import Settings
from wild_catalog.core.types import BoundingBox, Detection, GpsCoordinates
from wild_catalog.detection_processing_pipeline.detection_processing_pipeline import (
    DetectionProcessingPipeline,
)
from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.image_cropper.image_cropping import ImageCropper
from wild_catalog.logit_conditioning import LogitConditioner
from wild_catalog.range_data.class_index import ClassIndex
from wild_catalog.range_data.prior_mask import PriorMask
from wild_catalog.species_classifier.raw_classifier_output import RawClassifierOutput


class _Classifier:
    def __init__(self, predictions: list[Prediction]) -> None:
        self.predictions = predictions
        self.calls = []

    def classify(self, image: Image.Image) -> list[Prediction]:
        self.calls.append(image)
        return self.predictions


class _RawClassifier:
    def __init__(self) -> None:
        self.classify_calls = []
        self.classify_raw_calls = []

    def classify(self, image: Image.Image) -> list[Prediction]:
        self.classify_calls.append(image)
        return [
            Prediction(
                confidence=0.6,
                class_id=0,
                taxonomy=("raw-classifier-fallback",),
            )
        ]

    def classify_raw(self, image: Image.Image) -> RawClassifierOutput:
        self.classify_raw_calls.append(image)
        return RawClassifierOutput(
            probabilities=torch.tensor([[0.8, 0.2]]),
            class_index=ClassIndex(
                id="inat21",
                taxon_id_by_class_id={0: 10, 1: 20},
                taxonomy_path_by_class_id={
                    0: ("absent species",),
                    1: ("present species",),
                },
            ),
        )


class _RangePriorService:
    def __init__(self) -> None:
        self.calls = []

    def generate_prior_mask(self, gps_coordinates, class_index):
        self.calls.append((gps_coordinates, class_index))
        return PriorMask(
            values=torch.tensor([0.01, 1.0]),
            class_index_id=class_index.id,
        )


class _TaxonomyService:
    def __init__(self) -> None:
        self.calls = []

    def enrich_predictions(self, predictions, *, common_name_language):
        self.calls.append((predictions, common_name_language))
        return tuple(
            prediction
            if prediction.taxonomy_rank_names
            else replace(
                prediction,
                taxonomy_rank_names=("species",) * len(prediction.taxonomy),
            )
            for prediction in predictions
        )


class _EnrichingTaxonomyService:
    def __init__(self) -> None:
        self.calls = []

    def enrich_predictions(self, predictions, *, common_name_language):
        self.calls.append((predictions, common_name_language))
        return tuple(
            Prediction(
                confidence=prediction.confidence,
                is_present=prediction.is_present,
                taxonomy=("animalia", "aythya", "AFFINIS", "BOREALIS"),
                taxonomy_common_names=(
                    "animales",
                    "patos buceadores",
                    "black-bellied bewick's wren",
                ),
                class_id=prediction.class_id,
                taxon_id=prediction.taxon_id,
                taxonomy_rank_names=("kingdom", "genus", "species", "subspecies"),
            )
            for prediction in predictions
        )


def test_detection_processing_pipeline_requires_taxonomy_service() -> None:
    with pytest.raises(ValueError, match="taxonomy_service is required"):
        DetectionProcessingPipeline(
            ImageCropper(Settings()),
            _Classifier([]),
            taxonomy_service=None,
        )


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
                taxonomy_rank_names=("species",),
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
        taxonomy_service=_TaxonomyService(),
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
    assert result.predictions == (
        Prediction(
            confidence=0.72,
            is_present=True,
            taxonomy=("mallard",),
            taxonomy_common_names=("Mallard",),
            class_id=17,
            taxonomy_rank_names=("species",),
        ),
    )


def test_detection_processing_pipeline_enriches_predictions_with_requested_language() -> None:
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
                taxon_id=6930,
                taxonomy_rank_names=("species",),
            )
        ]
    )
    taxonomy_service = _EnrichingTaxonomyService()

    result = DetectionProcessingPipeline(
        ImageCropper(Settings()),
        classifier,
        taxonomy_service=taxonomy_service,
    ).process(
        image,
        detection,
        common_name_language="es-MX",
    )

    assert taxonomy_service.calls == [(tuple(classifier.predictions), "es-MX")]
    assert result.predictions[0].taxonomy == (
        "Animalia",
        "Aythya",
        "affinis",
        "borealis",
    )
    assert result.predictions[0].taxonomy_common_names == (
        "Animales",
        "Patos Buceadores",
        "Black-Bellied Bewick's Wren",
    )


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
        taxonomy_service=_TaxonomyService(),
    ).process(image, detection)

    assert result.predictions == ()


def test_detection_processing_pipeline_applies_range_prior_when_gps_is_available() -> None:
    image = Image.new("RGB", (100, 120), color=(255, 0, 0))
    detection = Detection(
        box=BoundingBox(xmin=1, ymin=2, xmax=11, ymax=22),
        confidence=0.87,
        class_id=3,
        label="animal",
    )
    classifier = _RawClassifier()
    range_prior_service = _RangePriorService()
    gps_coordinates = GpsCoordinates(latitude=29.7604, longitude=-95.3698)

    result = DetectionProcessingPipeline(
        ImageCropper(
            Settings(
                crop_margin_ratio=0.1,
                crop_margin_min_px=8,
            )
        ),
        classifier,
        range_prior_service=range_prior_service,
        logit_conditioner=LogitConditioner(gamma=2.0, epsilon=1e-12, top_k=2),
        taxonomy_service=_TaxonomyService(),
    ).process(image, detection, gps_coordinates)

    assert classifier.classify_calls == []
    assert classifier.classify_raw_calls == [result.cropped_image]
    assert range_prior_service.calls[0][0] == gps_coordinates
    assert [prediction.class_id for prediction in result.predictions] == [1, 0]
    assert result.predictions[0].taxonomy == ("present species",)


def test_detection_processing_pipeline_uses_classifier_when_gps_is_missing() -> None:
    image = Image.new("RGB", (100, 120), color=(255, 0, 0))
    detection = Detection(
        box=BoundingBox(xmin=1, ymin=2, xmax=11, ymax=22),
        confidence=0.87,
        class_id=3,
        label="animal",
    )
    classifier = _RawClassifier()

    result = DetectionProcessingPipeline(
        ImageCropper(
            Settings(
                crop_margin_ratio=0.1,
                crop_margin_min_px=8,
            )
        ),
        classifier,
        range_prior_service=_RangePriorService(),
        taxonomy_service=_TaxonomyService(),
    ).process(image, detection)

    assert classifier.classify_calls == [result.cropped_image]
    assert classifier.classify_raw_calls == []
    assert result.predictions[0].taxonomy == ("raw-classifier-fallback",)
