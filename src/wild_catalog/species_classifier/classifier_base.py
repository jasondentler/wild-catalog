from abc import ABC, abstractmethod

from PIL import Image

from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.species_classifier.raw_classifier_output import RawClassifierOutput


class Classifier(ABC):
    """Interface for wildlife classifier."""

    @abstractmethod
    def classify(self, image: Image.Image) -> list[Prediction]:
        """Return candidate wildlife species for a normalized RGB cropped image."""

    def classify_raw(self, image: Image.Image) -> RawClassifierOutput:
        """Return raw class probabilities before ranking or filtering."""
        raise NotImplementedError("Raw classifier output is not available.")
