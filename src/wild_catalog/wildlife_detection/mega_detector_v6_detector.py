from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from wild_catalog.core.types import BoundingBox, Detection
from wild_catalog.wildlife_detection.detector_base import Detector
from wild_catalog.wildlife_detection.device import get_torch_device
from wild_catalog.wildlife_detection.megadetector_factory import (
    get_megadetector_v6_factory,
)
from wild_catalog.wildlife_detection.pytorch_wildlife_stdout import (
    suppress_pytorch_wildlife_model_load_stdout,
)
from wild_catalog.wildlife_detection.torch_hub_cache import configure_torch_hub_dir

DEFAULT_CONFIDENCE_THRESHOLD = 0.3
DEFAULT_MODEL_PATH = Path("models/MDV6-apa-rtdetr-e.pth")
DEFAULT_TORCH_HUB_DIR = Path("models/torch-hub")
DEFAULT_MODEL_VERSION = "MDV6-apa-rtdetr-e"

ModelFactory = Callable[..., Any]


class MegaDetectorV6Detector(Detector):
    """PyTorch-Wildlife MegaDetector v6 adapter."""

    def __init__(
        self,
        *,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        device: str | None = None,
        model: Any | None = None,
        model_factory: ModelFactory | None = None,
        model_weights: str | Path | None = None,
        model_version: str = DEFAULT_MODEL_VERSION,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.device = device or get_torch_device()
        self.model_weights = Path(model_weights) if model_weights is not None else None
        self.model_version = model_version
        self.model = model or self._load_model(model_factory)

    def detect(self, image: Image.Image) -> list[Detection]:
        """Process an in-memory PIL image using MegaDetector v6."""
        rgb_image = image.convert("RGB")
        result = self.model.single_image_detection(
            np.asarray(rgb_image),
            det_conf_thres=self.confidence_threshold,
        )
        return self._parse_result(result)

    def _load_model(self, model_factory: ModelFactory | None) -> Any:
        configure_torch_hub_dir(DEFAULT_TORCH_HUB_DIR)
        factory = model_factory or get_megadetector_v6_factory()
        kwargs: dict[str, Any] = {
            "device": self.device,
            "pretrained": True,
            "version": self.model_version,
        }
        if self.model_weights is not None:
            kwargs["weights"] = str(self.model_weights)

        with suppress_pytorch_wildlife_model_load_stdout():
            return factory(**kwargs)

    def _parse_result(self, result: dict[str, Any]) -> list[Detection]:
        detections = result.get("detections")
        if detections is None:
            return []

        boxes = getattr(detections, "xyxy", None)
        confidences = getattr(detections, "confidence", None)
        class_ids = getattr(detections, "class_id", None)
        if boxes is None or confidences is None or class_ids is None:
            return []

        parsed: list[Detection] = []
        class_names = getattr(self.model, "CLASS_NAMES", {})
        for box, confidence, class_id in zip(boxes, confidences, class_ids, strict=False):
            confidence_value = float(confidence)
            if confidence_value <= self.confidence_threshold:
                continue

            class_id_value = int(class_id)
            parsed.append(
                Detection(
                    box=_to_bounding_box(box),
                    confidence=confidence_value,
                    class_id=class_id_value,
                    label=class_names.get(class_id_value),
                )
            )

        return parsed


def _to_bounding_box(box: Any) -> BoundingBox:
    xmin, ymin, xmax, ymax = [int(round(float(coordinate))) for coordinate in box[:4]]
    return BoundingBox(xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax)
