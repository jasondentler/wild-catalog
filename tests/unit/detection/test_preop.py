from PIL import Image

from wild_catalog.detection import preop


class FakeDetector:
    def __init__(self) -> None:
        self.received_image = None

    def locate_objects(self, image):
        self.received_image = image
        return []


def test_preop_detector_model_builds_detector_and_runs_inference(monkeypatch) -> None:
    fake_detector = FakeDetector()

    monkeypatch.setattr(
        preop,
        "build_detector",
        lambda settings: fake_detector,
    )

    preop.preop_detector_model()

    assert isinstance(fake_detector.received_image, Image.Image)
    assert fake_detector.received_image.mode == "RGB"
