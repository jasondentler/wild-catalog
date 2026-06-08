from types import SimpleNamespace

import pytest
import torch
from PIL import Image

from wild_catalog.core.config import Settings
from wild_catalog.core.errors import ModelUnavailableError
from wild_catalog.detection import grounding_dino
from wild_catalog.detection.grounding_dino import GroundingDinoObjectDetector
from wild_catalog.detection.types import DetectionCategory


class FakeInputs(dict):
    def __init__(self) -> None:
        super().__init__({"input_ids": torch.tensor([[1, 2, 3]])})
        self.device = None

    def to(self, device):
        self.device = device
        return self


class FakeProcessor:
    def __init__(self) -> None:
        self.calls = []

    def __call__(self, *, images, text, return_tensors):
        self.calls.append((images, text, return_tensors))
        return FakeInputs()

    def post_process_grounded_object_detection(
        self,
        outputs,
        *,
        input_ids,
        threshold,
        text_threshold,
        target_sizes,
    ):
        assert outputs.ok is True
        assert input_ids.shape == (1, 3)
        assert threshold == 0.25
        assert text_threshold == 0.25
        assert target_sizes == [(40, 80)]
        return [
            {
                "scores": torch.tensor([0.91, 0.5, 0.1]),
                "boxes": torch.tensor(
                    [
                        [1.0, 2.0, 30.0, 35.0],
                        [5.0, 5.0, 50.0, 20.0],
                        [0.0, 0.0, 10.0, 10.0],
                    ]
                ),
                "text_labels": ["Bird.", "vehicle", "flower"],
            }
        ]


class FakeModel:
    def __init__(self) -> None:
        self.device = None
        self.eval_called = False
        self.call_count = 0

    def to(self, device):
        self.device = device
        return self

    def eval(self) -> None:
        self.eval_called = True

    def __call__(self, **kwargs):
        self.call_count += 1
        return SimpleNamespace(ok=True)


def test_grounding_dino_detector_runs_inference_with_configured_prompt() -> None:
    fake_processor = FakeProcessor()
    fake_model = FakeModel()
    settings = Settings(grounding_dino_prompt="bird . plant .")

    detector = GroundingDinoObjectDetector(
        settings,
        processor_loader=lambda model_id: fake_processor,
        model_loader=lambda model_id: fake_model,
    )

    detections = detector.locate_objects(Image.new("RGB", (80, 40), color=(128, 128, 128)))

    assert fake_model.eval_called is True
    assert fake_model.call_count == 1
    assert fake_processor.calls[0][1] == "bird . plant ."
    assert detections[0].category is DetectionCategory.ANIMAL
    assert detections[0].label == "bird"
    assert detections[0].bounding_box.xmax <= 80
    assert detections[0].bounding_box.ymax <= 40


def test_grounding_dino_warmup_loads_model_without_inference() -> None:
    fake_processor = FakeProcessor()
    fake_model = FakeModel()
    detector = GroundingDinoObjectDetector(
        Settings(),
        processor_loader=lambda model_id: fake_processor,
        model_loader=lambda model_id: fake_model,
    )

    detector.warmup()

    assert fake_model.eval_called is True
    assert fake_model.call_count == 0


def test_from_pretrained_uses_local_cache_first(monkeypatch) -> None:
    class Factory:
        calls = []

        @classmethod
        def from_pretrained(cls, model_id, **kwargs):
            cls.calls.append((model_id, kwargs))
            return "loaded"

    monkeypatch.setattr(
        grounding_dino.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [object()],
    )

    loaded = grounding_dino._from_pretrained_with_local_cache_fallback(
        Factory,
        "model-id",
        artifact_name="artifact",
    )

    assert loaded == "loaded"
    assert Factory.calls == [("model-id", {"local_files_only": True})]


def test_from_pretrained_offline_mode_fails_without_online_retry(monkeypatch) -> None:
    class Factory:
        calls = []

        @classmethod
        def from_pretrained(cls, model_id, **kwargs):
            cls.calls.append((model_id, kwargs))
            raise OSError("not cached")

    monkeypatch.setenv("HF_HUB_OFFLINE", "1")

    with pytest.raises(ModelUnavailableError):
        grounding_dino._from_pretrained_with_local_cache_fallback(
            Factory,
            "model-id",
            artifact_name="artifact",
        )

    assert Factory.calls == [("model-id", {"local_files_only": True})]


def test_from_pretrained_dns_failure_fails_before_online_retry(monkeypatch) -> None:
    class Factory:
        calls = []

        @classmethod
        def from_pretrained(cls, model_id, **kwargs):
            cls.calls.append((model_id, kwargs))
            raise OSError("not cached")

    def fail_dns(*args, **kwargs):
        raise OSError("dns failed")

    monkeypatch.setattr(grounding_dino.socket, "getaddrinfo", fail_dns)

    with pytest.raises(ModelUnavailableError):
        grounding_dino._from_pretrained_with_local_cache_fallback(
            Factory,
            "model-id",
            artifact_name="artifact",
        )

    assert Factory.calls == []
