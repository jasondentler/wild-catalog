
from functools import lru_cache

from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.settings import Settings
from wild_catalog.deduplicate_detections.detection_deduplicator import DetectionDeduplicator
from wild_catalog.detection_processing_pipeline.detection_processing_pipeline import (
    DetectionProcessingPipeline,
)
from wild_catalog.identify_pipeline.identify_pipeline import IdentifyPipeline
from wild_catalog.image_cropper.image_cropping import ImageCropper
from wild_catalog.species_classifier.classifier import SpeciesClassifier
from wild_catalog.wildlife_detection.detector import WildlifeDetector


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def get_identify_pipeline() -> IdentifyPipeline:
    settings = get_settings()
    conversion = ImageConversionService(settings)
    wildlife_detector = WildlifeDetector()
    detection_deduplicator = DetectionDeduplicator()
    species_classifier = SpeciesClassifier(
        settings,
        device=getattr(wildlife_detector, "device", None),
    )
    detection_processing_pipeline = DetectionProcessingPipeline(
        ImageCropper(settings),
        species_classifier,
    )

    return IdentifyPipeline(
        settings,
        conversion,
        wildlife_detector,
        detection_deduplicator=detection_deduplicator,
        detection_processing_pipeline=detection_processing_pipeline,
    )
