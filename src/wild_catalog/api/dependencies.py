
from functools import lru_cache

from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.settings import Settings
from wild_catalog.deduplicate_detections.detection_deduplicator import DetectionDeduplicator
from wild_catalog.detection_processing_pipeline.detection_processing_pipeline import (
    DetectionProcessingPipeline,
)
from wild_catalog.identify_pipeline.identify_pipeline import IdentifyPipeline
from wild_catalog.image_cropper.image_cropping import ImageCropper
from wild_catalog.logit_conditioning import LogitConditioner
from wild_catalog.range_data.sqlite_species_range_store import SQLiteSpeciesRangeStore
from wild_catalog.range_data.species_range_prior_service import SpeciesRangePriorService
from wild_catalog.species_classifier.classifier import SpeciesClassifier
from wild_catalog.wildlife_detection.detector import WildlifeDetector


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache(maxsize=1)
def get_identify_pipeline() -> IdentifyPipeline:
    settings = get_settings()
    conversion = ImageConversionService(settings)
    wildlife_detector = WildlifeDetector()
    detection_deduplicator = DetectionDeduplicator()
    range_store = SQLiteSpeciesRangeStore(settings.range_store_database_path)
    species_classifier = SpeciesClassifier(
        settings,
        device=getattr(wildlife_detector, "device", None),
        taxon_id_by_scientific_name=range_store.get_taxon_ids_by_names,
    )
    detection_processing_pipeline = DetectionProcessingPipeline(
        ImageCropper(settings),
        species_classifier,
        range_prior_service=SpeciesRangePriorService(settings, store=range_store),
        logit_conditioner=LogitConditioner(
            gamma=settings.logit_conditioning_gamma,
            epsilon=settings.logit_conditioning_epsilon,
            top_k=settings.species_classifier_top_k,
        ),
    )

    return IdentifyPipeline(
        settings,
        conversion,
        wildlife_detector,
        detection_deduplicator=detection_deduplicator,
        detection_processing_pipeline=detection_processing_pipeline,
    )
