from abc import ABC, abstractmethod

from PIL import Image

from wild_catalog.identify_pipeline.prediction import Prediction


class Classifier(ABC):
    """Interface for wildlife classifier."""

    @abstractmethod
    def classify(self, image: Image.Image) -> list[Prediction]:
        """Return candidate wildlife species for a normalized RGB cropped image."""
