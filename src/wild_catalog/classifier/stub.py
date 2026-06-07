from collections.abc import Sequence

import torch
from PIL import Image

from wild_catalog.classifier.types import ClassifierMetadata, ClassIndex, RawClassifierOutput


class StubSpeciesClassifier:
    @property
    def metadata(self) -> ClassifierMetadata:
        return ClassifierMetadata(
            backend="stub",
            model_id="stub-species-classifier",
            class_count=1,
            class_index_id="stub-inat",
            output_type="logits",
            taxonomy_source="stub",
        )

    def predict_species(
        self,
        cropped_images: Sequence[Image.Image],
    ) -> RawClassifierOutput:
        return RawClassifierOutput(
            logits=torch.empty((len(cropped_images), 1)),
            class_index=ClassIndex(
                id="stub-inat",
                taxon_id_by_class_id={0: 1},
            ),
        )
