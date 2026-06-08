from PIL import Image

from wild_catalog.core.config import Settings
from wild_catalog.detection import preop


class FakeDetector:
    def __init__(self) -> None:
        self.received_image = None
        self.warmup_called = False

    def locate_objects(self, image):
        self.received_image = image
        return []

    def warmup(self) -> None:
        self.warmup_called = True


def test_preop_detector_model_builds_detector_and_runs_inference(monkeypatch) -> None:
    fake_detector = FakeDetector()

    monkeypatch.setattr(
        preop,
        "build_detector",
        lambda settings: fake_detector,
    )

    preop.preop_detector_model()

    assert fake_detector.warmup_called is True
    assert fake_detector.received_image is None


def test_preop_detector_model_falls_back_to_inference_without_warmup(monkeypatch) -> None:
    class DetectorWithoutWarmup:
        def __init__(self) -> None:
            self.received_image = None

        def locate_objects(self, image):
            self.received_image = image
            return []

    fake_detector = DetectorWithoutWarmup()

    monkeypatch.setattr(
        preop,
        "build_detector",
        lambda settings: fake_detector,
    )

    preop.preop_detector_model()

    assert isinstance(fake_detector.received_image, Image.Image)
    assert fake_detector.received_image.mode == "RGB"


def test_detector_preop_settings_default_to_real_grounding_dino_detector() -> None:
    settings = preop._detector_preop_settings(Settings())

    assert settings.detector_backend == "grounding-dino"


def test_detector_preop_settings_preserve_configured_backend() -> None:
    settings = preop._detector_preop_settings(Settings(detector_backend="custom-detector"))

    assert settings.detector_backend == "custom-detector"
