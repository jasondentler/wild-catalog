
from functools import lru_cache

from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.settings import Settings
from wild_catalog.deduplicate_detections.detection_deduplicator import DetectionDeduplicator
from wild_catalog.detection_processing_pipeline.detection_processing_pipeline import (
    DetectionProcessingPipeline,
)
from wild_catalog.identify_pipeline.identify_pipeline import IdentifyPipeline
from wild_catalog.wildlife_detection.detector import WildlifeDetector


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def get_identify_pipeline() -> IdentifyPipeline:
    settings = get_settings()
    conversion = ImageConversionService(settings)
    wildlife_detector = WildlifeDetector()
    detection_deduplicator = DetectionDeduplicator()
    detection_processing_pipeline = DetectionProcessingPipeline()

    return IdentifyPipeline(
        settings,
        conversion,
        wildlife_detector,
        detection_deduplicator=detection_deduplicator,
        detection_processing_pipeline=detection_processing_pipeline,
    )
