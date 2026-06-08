from datetime import datetime
from io import BytesIO
from typing import BinaryIO

import torch
from PIL import Image

from wild_catalog.classifier.types import (
    ClassifierMetadata,
    ClassIndex,
    ClassPrediction,
    RawClassifierOutput,
)
from wild_catalog.conversion.types import ConvertedImage
from wild_catalog.core.config import Settings
from wild_catalog.core.types import BoundingBox, GpsCoordinates
from wild_catalog.cropping.types import CropResult
from wild_catalog.detection.types import Detection, DetectionCategory
from wild_catalog.pipeline.identify import IdentifyPipeline
from wild_catalog.pipeline.models import ExifOverride, IdentifyCommand
from wild_catalog.prior.types import PresenceResult, PriorMask
from wild_catalog.taxonomy.types import EnrichedPrediction


class FakeConverter:
    def __init__(self) -> None:
        self.gps_coordinates_override: GpsCoordinates | None = None
        self.captured_at_override: datetime | None = None

    def process_and_extract_metadata(
        self,
        image_file: BinaryIO,
        original_filename: str,
        gps_coordinates_override: GpsCoordinates | None = None,
        captured_at_override: datetime | None = None,
    ) -> ConvertedImage:
        self.gps_coordinates_override = gps_coordinates_override
        self.captured_at_override = captured_at_override

        return ConvertedImage(
            image=Image.new("RGB", (100, 100)),
            original_filename=original_filename,
            gps_coordinates=GpsCoordinates(latitude=29.0, longitude=-95.0),
            captured_at=None,
            detected_format="jpeg",
        )


class FakeDetector:
    def locate_objects(self, image: Image.Image) -> list[Detection]:
        return [
            Detection(
                bounding_box=BoundingBox(10, 10, 30, 30),
                confidence=0.9,
                label="bird",
                category=DetectionCategory.ANIMAL,
                source="fake",
            )
        ]


class FakeDetectorWithNoDetections:
    def locate_objects(self, image: Image.Image) -> list[Detection]:
        return []


class FakeDetectorWithManyDetections:
    def locate_objects(self, image: Image.Image) -> list[Detection]:
        return [
            Detection(
                bounding_box=BoundingBox(index, index, index + 10, index + 10),
                confidence=0.9,
                label="bird",
                category=DetectionCategory.ANIMAL,
                source="fake",
            )
            for index in range(5)
        ]


class FakeDeduplicator:
    def filter_overlapping_detections(self, detections: list[Detection]) -> list[Detection]:
        return detections


class FakeCropper:
    def extract_target_regions(
        self,
        image: Image.Image,
        detections: list[Detection],
    ) -> list[CropResult]:
        if not detections:
            return []

        return [
            CropResult(
                index=0,
                detection=detections[0],
                bounding_box=detections[0].bounding_box,
                bounding_box_with_margin=BoundingBox(5, 5, 35, 35),
                image=Image.new("RGB", (30, 30)),
            )
        ]


class RecordingCropper:
    def __init__(self) -> None:
        self.received_detection_count = 0

    def extract_target_regions(
        self,
        image: Image.Image,
        detections: list[Detection],
    ) -> list[CropResult]:
        self.received_detection_count = len(detections)
        return []


class FakeClassifier:
    @property
    def metadata(self) -> ClassifierMetadata:
        return ClassifierMetadata(
            backend="fake",
            model_id="fake-model",
            class_count=2,
            class_index_id="fake-index",
            output_type="logits",
            taxonomy_source="fake-taxonomy",
        )

    def predict_species(self, cropped_images: list[Image.Image]) -> RawClassifierOutput:
        return RawClassifierOutput(
            logits=torch.tensor([[3.0, 1.0]], dtype=torch.float32),
            class_index=ClassIndex(
                id="fake-index",
                taxon_id_by_class_id={
                    0: 101,
                    1: 202,
                },
            ),
        )


class FakePriorService:
    def generate_prior_mask(
        self,
        gps_coordinates: GpsCoordinates | None,
        class_index: ClassIndex,
    ) -> PriorMask:
        return PriorMask(
            values=torch.tensor([1.0, 0.01], dtype=torch.float32),
            class_index_id=class_index.id,
        )

    def get_presence_for_taxa(
        self,
        gps_coordinates: GpsCoordinates | None,
        taxon_ids: set[int],
    ) -> PresenceResult:
        return PresenceResult(
            is_present_by_taxon_id={
                taxon_id: taxon_id == 101 for taxon_id in taxon_ids
            }
        )


class FakeConditioner:
    def apply_geographic_prior(
        self,
        classifier_output: RawClassifierOutput,
        prior_mask: PriorMask,
    ) -> list[list[ClassPrediction]]:
        return [
            [
                ClassPrediction(class_id=0, confidence=0.95),
                ClassPrediction(class_id=1, confidence=0.05),
            ]
        ]


class FakeTaxonomyService:
    def enrich_predictions(
        self,
        predictions: list[ClassPrediction],
        class_index: ClassIndex,
        common_name_language: str,
        presence_by_taxon_id: dict[int, bool],
    ) -> list[EnrichedPrediction]:
        return [
            EnrichedPrediction(
                class_id=prediction.class_id,
                taxon_id=class_index.taxon_id_by_class_id[prediction.class_id],
                accepted_taxon_id=class_index.taxon_id_by_class_id[prediction.class_id],
                confidence=prediction.confidence,
                is_present=presence_by_taxon_id[
                    class_index.taxon_id_by_class_id[prediction.class_id]
                ],
                taxonomy=("Animalia", "Aves", "Fake bird"),
                taxonomy_common_names=("Animals", "Birds", "Fake Bird"),
                taxonomy_rank_names=("kingdom", "class", "species"),
            )
            for prediction in predictions
        ]


class RecordingTaxonomyService(FakeTaxonomyService):
    def __init__(self) -> None:
        self.common_name_language: str | None = None

    def enrich_predictions(
        self,
        predictions: list[ClassPrediction],
        class_index: ClassIndex,
        common_name_language: str,
        presence_by_taxon_id: dict[int, bool],
    ) -> list[EnrichedPrediction]:
        self.common_name_language = common_name_language
        return super().enrich_predictions(
            predictions=predictions,
            class_index=class_index,
            common_name_language=common_name_language,
            presence_by_taxon_id=presence_by_taxon_id,
        )


class FailsIfCalled:
    def __getattr__(self, name: str):
        raise AssertionError(f"{name} should not have been called")


def make_pipeline(
    *,
    settings: Settings | None = None,
    converter: FakeConverter | None = None,
    detector=None,
    deduplicator=None,
    cropper=None,
    prior_service=None,
    classifier=None,
    conditioner=None,
    taxonomy_service: FakeTaxonomyService | None = None,
) -> IdentifyPipeline:
    return IdentifyPipeline(
        settings=settings or Settings(max_detections=10),
        converter=converter or FakeConverter(),
        detector=detector or FakeDetector(),
        deduplicator=deduplicator or FakeDeduplicator(),
        cropper=cropper or FakeCropper(),
        prior_service=prior_service or FakePriorService(),
        classifier=classifier or FakeClassifier(),
        conditioner=conditioner or FakeConditioner(),
        taxonomy_service=taxonomy_service or FakeTaxonomyService(),
    )


def test_identify_orchestrates_services_and_returns_identified_object() -> None:
    pipeline = make_pipeline()

    result = pipeline.identify(
        image_file=BytesIO(b"fake"),
        command=IdentifyCommand(
            original_filename="test.jpg",
            common_name_language="en-US",
        ),
    )

    assert len(result.objects) == 1

    identified_object = result.objects[0]

    assert identified_object.bounding_box == BoundingBox(10, 10, 30, 30)
    assert identified_object.bounding_box_with_margin == BoundingBox(5, 5, 35, 35)
    assert identified_object.gps_coordinates == GpsCoordinates(
        latitude=29.0,
        longitude=-95.0,
    )
    assert identified_object.cropped_image is None

    assert len(identified_object.predictions) == 2
    assert identified_object.predictions[0].taxonomy[-1] == "Fake bird"
    assert identified_object.predictions[0].taxonomy_common_names[-1] == "Fake Bird"
    assert identified_object.predictions[0].is_present is True


def test_identify_includes_cropped_image_when_requested() -> None:
    pipeline = make_pipeline()

    result = pipeline.identify(
        image_file=BytesIO(b"fake"),
        command=IdentifyCommand(
            original_filename="test.jpg",
            return_detected_images=True,
        ),
    )

    assert len(result.objects) == 1
    assert result.objects[0].cropped_image is not None


def test_identify_returns_empty_result_when_no_objects_detected() -> None:
    pipeline = make_pipeline(
        detector=FakeDetectorWithNoDetections(),
        classifier=FailsIfCalled(),
        prior_service=FailsIfCalled(),
        conditioner=FailsIfCalled(),
        taxonomy_service=FailsIfCalled(),
    )

    result = pipeline.identify(
        image_file=BytesIO(b"fake"),
        command=IdentifyCommand(original_filename="test.jpg"),
    )

    assert result.objects == ()


def test_identify_applies_max_detections_before_cropping() -> None:
    cropper = RecordingCropper()
    pipeline = make_pipeline(
        settings=Settings(max_detections=2),
        detector=FakeDetectorWithManyDetections(),
        cropper=cropper,
    )

    pipeline.identify(
        image_file=BytesIO(b"fake"),
        command=IdentifyCommand(original_filename="test.jpg"),
    )

    assert cropper.received_detection_count == 2


def test_identify_forwards_common_name_language_to_taxonomy_service() -> None:
    taxonomy_service = RecordingTaxonomyService()
    pipeline = make_pipeline(taxonomy_service=taxonomy_service)

    pipeline.identify(
        image_file=BytesIO(b"fake"),
        command=IdentifyCommand(
            original_filename="test.jpg",
            common_name_language="es-MX",
        ),
    )

    assert taxonomy_service.common_name_language == "es-MX"


def test_identify_forwards_exif_override_to_conversion_service() -> None:
    captured_at = datetime(2026, 5, 1, 12, 30)
    gps_coordinates = GpsCoordinates(latitude=29.7604, longitude=-95.3698)
    converter = FakeConverter()
    pipeline = make_pipeline(converter=converter)

    pipeline.identify(
        image_file=BytesIO(b"fake"),
        command=IdentifyCommand(
            original_filename="test.jpg",
            exif_override=ExifOverride(
                gps_coordinates=gps_coordinates,
                captured_at=captured_at,
            ),
        ),
    )

    assert converter.gps_coordinates_override == gps_coordinates
    assert converter.captured_at_override == captured_at
