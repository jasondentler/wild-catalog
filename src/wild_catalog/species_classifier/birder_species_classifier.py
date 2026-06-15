from collections.abc import Callable
from typing import Any

import numpy as np
import torch
from PIL import Image

from wild_catalog.core.settings import Settings
from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.species_classifier.classifier_base import Classifier
from wild_catalog.wildlife_detection.device import get_torch_device

DEFAULT_MODEL_NAME = "hieradet_d_small_dino-v2-inat21"

ModelLoader = Callable[..., tuple[Any, Any, Callable[..., torch.Tensor]]]
InferImage = Callable[..., tuple[np.ndarray, np.ndarray | None]]


class BirderSpeciesClassifier(Classifier):
    """Birder adapter for species classification."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        device: str | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
        top_k: int | None = None,
        model: Any | None = None,
        model_info: Any | None = None,
        transform: Callable[..., torch.Tensor] | None = None,
        model_loader: ModelLoader | None = None,
        infer_image: InferImage | None = None,
    ) -> None:
        settings = settings or Settings()
        self.device = torch.device(device or get_torch_device())
        self.model_name = model_name
        self.top_k = top_k if top_k is not None else settings.species_classifier_top_k
        self._infer_image = infer_image or self._get_infer_image()

        if model is None or model_info is None or transform is None:
            model, model_info, transform = self._load_model(model_loader)

        self.model = model
        self.transform = transform
        self.class_to_idx = dict(model_info.class_to_idx)
        self._idx_to_class = {
            class_id: label for label, class_id in self.class_to_idx.items()
        }

    def classify(self, image: Image.Image) -> list[Prediction]:
        rgb_image = image.convert("RGB")
        with torch.inference_mode():
            probabilities, _ = self._infer_image(
                self.model,
                rgb_image,
                self.transform,
                device=self.device,
            )

        return self._to_predictions(probabilities)

    def _load_model(
        self,
        model_loader: ModelLoader | None,
    ) -> tuple[Any, Any, Callable[..., torch.Tensor]]:
        if model_loader is None:
            import birder.net  # noqa: F401
            from birder import load_pretrained_model_and_transform

            model_loader = load_pretrained_model_and_transform

        return model_loader(
            self.model_name,
            inference=True,
            device=self.device,
            progress_bar=False,
        )

    @staticmethod
    def _get_infer_image() -> InferImage:
        from birder.inference.classification import infer_image

        return infer_image

    def _to_predictions(self, probabilities: np.ndarray) -> list[Prediction]:
        flattened_probabilities = np.asarray(probabilities).reshape(-1)
        top_indices = np.argsort(flattened_probabilities)[::-1][: self.top_k]

        return [
            Prediction(
                confidence=float(flattened_probabilities[class_id]),
                is_present=True,
                taxonomy=(self._idx_to_class.get(int(class_id), str(class_id)),),
                taxonomy_common_names=(
                    self._idx_to_class.get(int(class_id), str(class_id)),
                ),
                class_id=int(class_id),
            )
            for class_id in top_indices
        ]
