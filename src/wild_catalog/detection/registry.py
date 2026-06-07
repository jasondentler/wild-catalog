from wild_catalog.core.config import Settings
from wild_catalog.detection.protocols import ObjectDetector


def build_detector(settings: Settings) -> ObjectDetector:
    raise NotImplementedError("Detector registry is not implemented yet.")
