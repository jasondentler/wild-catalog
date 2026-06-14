from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from wild_catalog.core.types import BoundingBox, Detection
from wild_catalog.wildlife_detection import mega_detector_v6_detector as detector_module
from wild_catalog.wildlife_detection.detector import (
    DEFAULT_CONFIDENCE_THRESHOLD,
    DEFAULT_MODEL_VERSION,
    Detector,
    MegaDetectorV6Detector,
    WildlifeDetector,
)


def _fake_pytorch_wildlife_detections() -> SimpleNamespace:
    return SimpleNamespace(
        xyxy=[
            [1.2, 2.3, 30.4, 40.5],
            [10, 20, 30, 40],
            [5, 6, 7, 8],
        ],
        confidence=[0.31, 0.3, 0.95],
        class_id=[0, 1, 2],
    )


def _fake_pytorch_wildlife_model():
    model = SimpleNamespace(
        CLASS_NAMES={0: "animal", 1: "person", 2: "vehicle"},
        received_image_shape=None,
        received_threshold=None,
    )

    def single_image_detection(image, *, det_conf_thres: float):
        model.received_image_shape = image.shape
        model.received_threshold = det_conf_thres
        return {"detections": _fake_pytorch_wildlife_detections()}

    model.single_image_detection = single_image_detection
    return model


def test_detector_interface_requires_detect_implementation() -> None:
    with pytest.raises(TypeError):
        Detector()


def test_wildlife_detector_default_alias_uses_megadetector_v6() -> None:
    assert WildlifeDetector is MegaDetectorV6Detector


def test_megadetector_v6_detector_loads_model_from_factory(monkeypatch) -> None:
    loaded = {}
    model = _fake_pytorch_wildlife_model()

    def fake_model_factory(**kwargs):
        loaded.update(kwargs)
        return model

    monkeypatch.setattr(detector_module, "get_torch_device", lambda: "cuda")

    detector = MegaDetectorV6Detector(
        model_factory=fake_model_factory,
        model_weights=Path("models/MDV6-apa-rtdetr-e.pth"),
    )

    assert detector.device == "cuda"
    assert detector.model is model
    assert loaded == {
        "device": "cuda",
        "pretrained": True,
        "version": DEFAULT_MODEL_VERSION,
        "weights": "models/MDV6-apa-rtdetr-e.pth",
    }


def test_megadetector_v6_detector_suppresses_pytorch_wildlife_load_print(capsys) -> None:
    model = _fake_pytorch_wildlife_model()

    def fake_model_factory(**kwargs):
        _ = kwargs
        print("before")
        print("Load PResNet101 state_dict")
        print("after")
        return model

    detector = MegaDetectorV6Detector(model_factory=fake_model_factory)

    assert detector.model is model
    assert capsys.readouterr().out == "before\nafter\n"


def test_detect_returns_project_detection_dataclasses() -> None:
    model = _fake_pytorch_wildlife_model()
    detector = MegaDetectorV6Detector(model=model)
    image = Image.new("RGBA", (32, 24), (1, 2, 3, 4))

    results = detector.detect(image)

    assert model.received_image_shape == (24, 32, 3)
    assert model.received_threshold == DEFAULT_CONFIDENCE_THRESHOLD
    assert results == [
        Detection(
            box=BoundingBox(xmin=1, ymin=2, xmax=30, ymax=40),
            confidence=0.31,
            class_id=0,
            label="animal",
        ),
        Detection(
            box=BoundingBox(xmin=5, ymin=6, xmax=7, ymax=8),
            confidence=0.95,
            class_id=2,
            label="vehicle",
        ),
    ]


def test_detect_returns_empty_list_when_backend_result_has_no_detections() -> None:
    model = _fake_pytorch_wildlife_model()
    model.single_image_detection = lambda image, *, det_conf_thres: {}
    detector = MegaDetectorV6Detector(model=model)

    assert detector.detect(Image.new("RGB", (1, 1))) == []
