from functools import lru_cache

from wild_catalog.classifier.registry import build_classifier
from wild_catalog.conditioning.service import LogitConditioner
from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.config import Settings
from wild_catalog.cropping.service import ImageCropper
from wild_catalog.deduplication.service import DetectionDeduplicator
from wild_catalog.detection.registry import build_detector
from wild_catalog.pipeline.identify import IdentifyPipeline
from wild_catalog.prior.service import SpeciesRangePriorService
from wild_catalog.taxonomy.service import TaxonomyService


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


@lru_cache(maxsize=1)
def get_identify_pipeline() -> IdentifyPipeline:
    settings = get_settings()

    return IdentifyPipeline(
        settings=settings,
        converter=ImageConversionService(settings),
        detector=build_detector(settings),
        deduplicator=DetectionDeduplicator(),
        cropper=ImageCropper(margin_ratio=settings.crop_margin_ratio),
        prior_service=SpeciesRangePriorService(settings),
        classifier=build_classifier(settings),
        conditioner=LogitConditioner(
            gamma=settings.prior_gamma,
            epsilon=settings.prior_epsilon,
            top_k=settings.classifier_top_k,
        ),
        taxonomy_service=TaxonomyService(settings),
    )


def clear_dependency_caches() -> None:
    get_settings.cache_clear()
    get_identify_pipeline.cache_clear()
