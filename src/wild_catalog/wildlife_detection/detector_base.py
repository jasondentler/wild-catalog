from abc import ABC, abstractmethod

from PIL import Image

from wild_catalog.core.types import Detection


class Detector(ABC):
    """Interface for wildlife localization backends."""

    @abstractmethod
    def detect(self, image: Image.Image) -> list[Detection]:
        """Return candidate wildlife detections for a normalized RGB image."""
