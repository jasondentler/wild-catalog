
from functools import lru_cache

from wild_catalog.conversion.service import ImageConversionService
from wild_catalog.core.settings import Settings
from wild_catalog.pipeline.identify_pipeline import IdentifyPipeline
from wild_catalog.wildlife_detection.detector import WildlifeDetector


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def get_identify_pipeline() -> None:
    settings = get_settings()
    conversion = ImageConversionService(settings)
    wildlife_detector = WildlifeDetector()

    return IdentifyPipeline(
        settings,
        conversion,
        wildlife_detector
    )
