from wild_catalog.wildlife_detection.detector_base import Detector
from wild_catalog.wildlife_detection.mega_detector_v6_detector import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_MODEL_PATH,
    DEFAULT_MODEL_VERSION,
    DEFAULT_TORCH_HUB_DIR,
    MegaDetectorV6Detector,
)

WildlifeDetector = MegaDetectorV6Detector

__all__ = [
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "DEFAULT_MODEL_PATH",
    "DEFAULT_MODEL_VERSION",
    "DEFAULT_TORCH_HUB_DIR",
    "Detector",
    "MegaDetectorV6Detector",
    "WildlifeDetector",
]
