from collections.abc import Sequence

import torch
from PIL import Image

from wild_catalog.classifier.protocols import SpeciesClassifier
from wild_catalog.classifier.types import ClassifierMetadata, ClassIndex, RawClassifierOutput


class StubSpeciesClassifier(SpeciesClassifier):
    def __init__(self) -> None:
        self._class_index = ClassIndex(
            id="stub",
            taxon_id_by_class_id={
                0: 1,
                1: 2,
                2: 3,
            },
        )
        self._metadata = ClassifierMetadata(
            backend="stub",
            model_id="stub",
            class_count=3,
            class_index_id=self._class_index.id,
            output_type="logits",
            taxonomy_source="stub",
        )

    @property
    def metadata(self) -> ClassifierMetadata:
        return self._metadata

    def predict_species(
        self,
        cropped_images: Sequence[Image.Image],
    ) -> RawClassifierOutput:
        logits = torch.tensor(
            [[4.0, 2.0, 1.0] for _ in cropped_images],
            dtype=torch.float32,
        )

        return RawClassifierOutput(
            logits=logits,
            class_index=self._class_index,
        )
