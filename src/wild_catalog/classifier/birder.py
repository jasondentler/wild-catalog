from collections.abc import Sequence
from pathlib import Path
from typing import Any

import torch
from PIL import Image

from wild_catalog.classifier.protocols import SpeciesClassifier
from wild_catalog.classifier.transforms import ensure_rgb_crops
from wild_catalog.classifier.types import ClassifierMetadata, ClassIndex, RawClassifierOutput
from wild_catalog.core.config import Settings
from wild_catalog.core.device import get_torch_device

_MODEL_ID = "hieradet_d_small_dino-v2-inat21"
_CLASS_INDEX_ID = "inat21"
_INAT21_CLASS_COUNT = 10_000


class BirderSpeciesClassifier(SpeciesClassifier):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._device = get_torch_device()
        self._model: torch.nn.Module | None = None
        self._transform: Any | None = None
        self._class_index: ClassIndex | None = None
        self._class_label_by_class_id: dict[int, str] = {}
        self._metadata = ClassifierMetadata(
            backend="birder",
            model_id=_MODEL_ID,
            class_count=_INAT21_CLASS_COUNT,
            class_index_id=_CLASS_INDEX_ID,
            output_type="logits",
            taxonomy_source=_CLASS_INDEX_ID,
        )

    @property
    def metadata(self) -> ClassifierMetadata:
        return self._metadata

    @property
    def class_label_by_class_id(self) -> dict[int, str]:
        self._ensure_loaded()
        return dict(self._class_label_by_class_id)

    def predict_species(
        self,
        cropped_images: Sequence[Image.Image],
    ) -> RawClassifierOutput:
        self._ensure_loaded()
        assert self._model is not None
        assert self._transform is not None
        assert self._class_index is not None

        if len(cropped_images) == 0:
            return RawClassifierOutput(
                logits=torch.empty(
                    (0, self._metadata.class_count),
                    dtype=torch.float32,
                    device=self._device,
                ),
                class_index=self._class_index,
            )

        logits_by_batch: list[torch.Tensor] = []
        rgb_crops = ensure_rgb_crops(cropped_images)

        with torch.inference_mode():
            for start in range(0, len(rgb_crops), self._settings.classifier_batch_size):
                batch_images = rgb_crops[start : start + self._settings.classifier_batch_size]
                batch = torch.stack(
                    [self._transform(image) for image in batch_images]
                ).to(self._device)
                logits = self._model(batch)
                logits_by_batch.append(logits.detach().float())

        return RawClassifierOutput(
            logits=torch.cat(logits_by_batch, dim=0),
            class_index=self._class_index,
        )

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return

        try:
            import birder
        except ImportError as exc:
            raise RuntimeError(
                "Unable to load Birder model `hieradet_d_small_dino-v2-inat21`. "
                "Ensure the Birder dependency is installed."
            ) from exc

        try:
            model, model_info, transform = birder.load_pretrained_model_and_transform(
                _MODEL_ID,
                dst=self._model_destination(),
                inference=True,
                device=self._device,
                progress_bar=False,
            )
        except Exception as exc:
            raise RuntimeError(
                "Unable to load Birder model `hieradet_d_small_dino-v2-inat21`. "
                "Ensure the model can be downloaded or loaded from the configured model cache."
            ) from exc

        model.eval()
        class_label_by_class_id = {
            class_id: label for label, class_id in model_info.class_to_idx.items()
        }
        self._class_label_by_class_id = class_label_by_class_id
        self._class_index = ClassIndex(
            id=_CLASS_INDEX_ID,
            taxon_id_by_class_id={
                class_id: _taxon_id_from_label(label, class_id)
                for class_id, label in class_label_by_class_id.items()
            },
        )
        self._metadata = ClassifierMetadata(
            backend="birder",
            model_id=_MODEL_ID,
            class_count=len(class_label_by_class_id),
            class_index_id=_CLASS_INDEX_ID,
            output_type="logits",
            taxonomy_source=_CLASS_INDEX_ID,
        )
        self._model = model
        self._transform = transform

    def _model_destination(self) -> Path | None:
        cache_path = self._settings.classifier_model_cache_path
        if cache_path is None:
            return None

        if cache_path.suffix:
            return cache_path

        return cache_path / f"{_MODEL_ID}.pt"


def _taxon_id_from_label(label: str, fallback: int) -> int:
    first_token = label.replace("_", " ", 1).split(maxsplit=1)[0].strip()
    if first_token.isdecimal():
        return int(first_token)

    return fallback
