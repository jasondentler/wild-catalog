import os
import socket
from collections.abc import Callable
from typing import Any

import torch
from PIL import Image

from wild_catalog.core.config import Settings
from wild_catalog.core.device import get_torch_device
from wild_catalog.core.errors import ModelUnavailableError, UnprocessableImageError
from wild_catalog.detection.grounding_dino_postprocess import (
    GroundingDinoPrediction,
    postprocess_grounding_dino_predictions,
)
from wild_catalog.detection.types import Detection

GROUNDING_DINO_SOURCE = "grounding-dino"

ProcessorLoader = Callable[[str], Any]
ModelLoader = Callable[[str], torch.nn.Module]


class GroundingDinoObjectDetector:
    def __init__(
        self,
        settings: Settings,
        *,
        processor_loader: ProcessorLoader | None = None,
        model_loader: ModelLoader | None = None,
    ) -> None:
        self._settings = settings
        self._device = get_torch_device()
        self._processor_loader = processor_loader
        self._model_loader = model_loader
        self._processor: Any | None = None
        self._model: torch.nn.Module | None = None

    def locate_objects(self, image: Image.Image) -> list[Detection]:
        self._ensure_loaded()
        assert self._processor is not None
        assert self._model is not None

        rgb_image = image.convert("RGB")
        width, height = rgb_image.size

        try:
            inputs = self._processor(
                images=rgb_image,
                text=self._settings.grounding_dino_prompt,
                return_tensors="pt",
            )
            inputs = inputs.to(self._device)

            with torch.inference_mode():
                outputs = self._model(**inputs)

            results = self._processor.post_process_grounded_object_detection(
                outputs,
                input_ids=inputs["input_ids"],
                threshold=self._settings.grounding_dino_box_threshold,
                text_threshold=self._settings.grounding_dino_text_threshold,
                target_sizes=[(height, width)],
            )
        except ModelUnavailableError:
            raise
        except Exception as exc:
            raise UnprocessableImageError(
                public_detail="The image could not be processed.",
                debug_detail="Grounding DINO inference failed.",
            ) from exc

        predictions = _predictions_from_processor_result(results[0])

        return postprocess_grounding_dino_predictions(
            predictions,
            image_width=width,
            image_height=height,
            confidence_threshold=self._settings.grounding_dino_box_threshold,
            boxes_are_normalized_cxcywh=False,
            source=GROUNDING_DINO_SOURCE,
        )

    def warmup(self) -> None:
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        if self._model is not None and self._processor is not None:
            return

        try:
            processor_loader = self._processor_loader or _load_default_processor
            model_loader = self._model_loader or _load_default_model
            processor = processor_loader(self._settings.grounding_dino_model_id)
            model = model_loader(self._settings.grounding_dino_model_id)
            model.to(self._device)
            model.eval()
        except ModelUnavailableError:
            self._processor = None
            self._model = None
            raise
        except Exception as exc:
            self._processor = None
            self._model = None
            raise ModelUnavailableError(
                public_detail="A required model is unavailable.",
                debug_detail=(
                    "Unable to load Grounding DINO model "
                    f"`{self._settings.grounding_dino_model_id}`."
                ),
            ) from exc

        self._processor = processor
        self._model = model


def _load_default_processor(model_id: str) -> Any:
    try:
        from transformers import AutoProcessor
    except ImportError as exc:
        raise ModelUnavailableError(
            public_detail="A required model is unavailable.",
            debug_detail="Transformers AutoProcessor is unavailable.",
        ) from exc

    return _from_pretrained_with_local_cache_fallback(
        AutoProcessor,
        model_id,
        artifact_name="Grounding DINO processor",
    )


def _load_default_model(model_id: str) -> torch.nn.Module:
    try:
        from transformers import AutoModelForZeroShotObjectDetection
    except ImportError as exc:
        raise ModelUnavailableError(
            public_detail="A required model is unavailable.",
            debug_detail="Transformers AutoModelForZeroShotObjectDetection is unavailable.",
        ) from exc

    return _from_pretrained_with_local_cache_fallback(
        AutoModelForZeroShotObjectDetection,
        model_id,
        artifact_name="Grounding DINO model",
    )


def _from_pretrained_with_local_cache_fallback(
    factory: Any,
    model_id: str,
    *,
    artifact_name: str,
) -> Any:
    if not _offline_mode_enabled():
        _ensure_huggingface_dns_resolves(artifact_name=artifact_name)

    try:
        return factory.from_pretrained(model_id, local_files_only=True)
    except Exception as local_exc:
        if _offline_mode_enabled():
            raise ModelUnavailableError(
                public_detail="A required model is unavailable.",
                debug_detail=f"{artifact_name} is not available in the local model cache.",
            ) from local_exc

        return factory.from_pretrained(model_id)


def _offline_mode_enabled() -> bool:
    return _truthy_env("HF_HUB_OFFLINE") or _truthy_env("TRANSFORMERS_OFFLINE")


def _truthy_env(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _ensure_huggingface_dns_resolves(*, artifact_name: str) -> None:
    try:
        socket.getaddrinfo("huggingface.co", 443)
    except OSError as exc:
        raise ModelUnavailableError(
            public_detail="A required model is unavailable.",
            debug_detail=(
                f"{artifact_name} is not available in the local model cache, "
                "and huggingface.co could not be resolved for download."
            ),
        ) from exc


def _predictions_from_processor_result(result: dict[str, Any]) -> list[GroundingDinoPrediction]:
    scores = _as_list(result["scores"])
    boxes = _as_list(result["boxes"])
    labels = result.get("text_labels", result.get("labels", []))

    return [
        GroundingDinoPrediction(
            box=tuple(float(value) for value in box),
            score=float(score),
            label=str(label),
        )
        for score, box, label in zip(scores, boxes, labels, strict=True)
    ]


def _as_list(value: Any) -> list[Any]:
    if hasattr(value, "detach"):
        return value.detach().cpu().tolist()

    if hasattr(value, "tolist"):
        return value.tolist()

    return list(value)
