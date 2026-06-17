from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image

from wild_catalog.core.settings import Settings
from wild_catalog.identify_pipeline.prediction import Prediction
from wild_catalog.range_data.class_index import ClassIndex
from wild_catalog.species_classifier.classifier_base import Classifier
from wild_catalog.species_classifier.raw_classifier_output import RawClassifierOutput
from wild_catalog.wildlife_detection.device import get_torch_device

DEFAULT_MODEL_NAME = "hieradet_d_small_dino-v2-inat21"
DEFAULT_MODELS_DIR = Path("data/models")

ModelLoader = Callable[..., tuple[Any, Any, Callable[..., torch.Tensor]]]
InferImage = Callable[..., tuple[np.ndarray, np.ndarray | None]]
TaxonIdLookup = Callable[[tuple[str, ...]], Mapping[str, int]]


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
        taxon_id_by_class_id: Mapping[int, int] | None = None,
        taxon_id_by_scientific_name: Mapping[str, int] | TaxonIdLookup | None = None,
    ) -> None:
        settings = settings or Settings()
        self.device = torch.device(device or get_torch_device())
        self.model_name = model_name
        self.models_dir = DEFAULT_MODELS_DIR
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
        self.class_index = self._build_class_index(
            taxon_id_by_class_id=taxon_id_by_class_id or {},
            taxon_id_by_scientific_name=self._resolve_taxon_ids_by_scientific_name(
                taxon_id_by_scientific_name,
            ),
        )

    def classify(self, image: Image.Image) -> list[Prediction]:
        raw_output = self.classify_raw(image)
        return self._to_predictions(raw_output.probabilities.detach().cpu().numpy())

    def classify_raw(self, image: Image.Image) -> RawClassifierOutput:
        rgb_image = image.convert("RGB")
        with torch.inference_mode():
            probabilities, _ = self._infer_image(
                self.model,
                rgb_image,
                self.transform,
                device=self.device,
            )

        return RawClassifierOutput(
            probabilities=self._to_probability_tensor(probabilities),
            class_index=self.class_index,
            label_by_class_id=self._idx_to_class,
        )

    def _load_model(
        self,
        model_loader: ModelLoader | None,
    ) -> tuple[Any, Any, Callable[..., torch.Tensor]]:
        if model_loader is None:
            import birder.net  # noqa: F401
            from birder import load_pretrained_model_and_transform
            from birder.conf import settings as birder_settings

            self.models_dir.mkdir(parents=True, exist_ok=True)
            birder_settings.MODELS_DIR = self.models_dir
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

    def _to_probability_tensor(self, probabilities: np.ndarray) -> torch.Tensor:
        probability_tensor = torch.as_tensor(
            probabilities,
            device=self.device,
        )

        if probability_tensor.ndim == 1:
            return probability_tensor.unsqueeze(0)

        return probability_tensor

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
                taxon_id=self.class_index.taxon_id_by_class_id.get(
                    int(class_id),
                    -1,
                ),
            )
            for class_id in top_indices
        ]

    def _build_class_index(
        self,
        *,
        taxon_id_by_class_id: Mapping[int, int],
        taxon_id_by_scientific_name: Mapping[str, int],
    ) -> ClassIndex:
        resolved_taxon_id_by_class_id = {
            class_id: taxon_id_by_class_id.get(
                class_id,
                self._range_taxon_id_for_label(
                    label,
                    class_id,
                    taxon_id_by_scientific_name,
                ),
            )
            for class_id, label in self._idx_to_class.items()
        }
        taxonomy_path_by_class_id = {
            class_id: (label,) for class_id, label in self._idx_to_class.items()
        }

        return ClassIndex(
            id=self.model_name,
            taxon_id_by_class_id=resolved_taxon_id_by_class_id,
            taxonomy_path_by_class_id=taxonomy_path_by_class_id,
        )

    def _resolve_taxon_ids_by_scientific_name(
        self,
        taxon_id_by_scientific_name: Mapping[str, int] | TaxonIdLookup | None,
    ) -> Mapping[str, int]:
        scientific_names = tuple(
            sorted(
                {
                    scientific_name
                    for label in self._idx_to_class.values()
                    if (scientific_name := self._scientific_name_from_label(label))
                }
            )
        )

        if taxon_id_by_scientific_name is None:
            return {}

        if callable(taxon_id_by_scientific_name):
            return taxon_id_by_scientific_name(scientific_names)

        return taxon_id_by_scientific_name

    @classmethod
    def _range_taxon_id_for_label(
        cls,
        label: str,
        class_id: int,
        taxon_id_by_scientific_name: Mapping[str, int],
    ) -> int:
        scientific_name = cls._scientific_name_from_label(label)
        if scientific_name is not None and scientific_name in taxon_id_by_scientific_name:
            return taxon_id_by_scientific_name[scientific_name]

        return cls._default_taxon_id(label, class_id)

    @staticmethod
    def _scientific_name_from_label(label: str) -> str | None:
        parts = label.split("_")

        if len(parts) < 2:
            return None

        genus, species = parts[-2:]
        if not genus or not species:
            return None

        return f"{genus} {species}"

    @staticmethod
    def _default_taxon_id(label: str, class_id: int) -> int:
        prefix = label.split("_", maxsplit=1)[0]

        if not prefix.isdecimal():
            return class_id

        return int(prefix)
