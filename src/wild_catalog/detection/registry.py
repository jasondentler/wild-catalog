from wild_catalog.core.config import Settings
from wild_catalog.detection.protocols import ObjectDetector
from wild_catalog.detection.stub import StubObjectDetector


def build_detector(settings: Settings) -> ObjectDetector:
    if settings.detector_backend == "stub":
        return StubObjectDetector()

    if settings.detector_backend == "grounding-dino":
        raise NotImplementedError("Grounding DINO detector backend is not implemented yet.")

    raise ValueError(f"Unknown detector backend: {settings.detector_backend}")
