from collections.abc import Sequence
from typing import Protocol

from PIL import Image

from wild_catalog.classifier.types import ClassifierMetadata, RawClassifierOutput


class SpeciesClassifier(Protocol):
    @property
    def metadata(self) -> ClassifierMetadata:
        ...

    def predict_species(
        self,
        cropped_images: Sequence[Image.Image],
    ) -> RawClassifierOutput:
        ...
