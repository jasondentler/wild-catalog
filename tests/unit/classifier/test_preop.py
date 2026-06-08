from PIL import Image

from wild_catalog.classifier import preop
from wild_catalog.core.config import Settings


class FakeClassifier:
    def __init__(self) -> None:
        self.received_images = None

    def predict_species(self, cropped_images):
        self.received_images = cropped_images


def test_preop_classifier_model_builds_classifier_and_runs_inference(monkeypatch) -> None:
    fake_classifier = FakeClassifier()

    monkeypatch.setattr(
        preop,
        "build_classifier",
        lambda settings: fake_classifier,
    )

    preop.preop_classifier_model()

    assert fake_classifier.received_images is not None
    assert len(fake_classifier.received_images) == 1
    assert isinstance(fake_classifier.received_images[0], Image.Image)
    assert fake_classifier.received_images[0].mode == "RGB"


def test_classifier_preop_settings_default_to_real_birder_model() -> None:
    settings = preop._classifier_preop_settings(Settings())

    assert settings.classifier_backend == "birder-inat21"
    assert settings.classifier_model_cache_path is not None
    assert str(settings.classifier_model_cache_path) == "data/models/classifier"


def test_classifier_preop_settings_preserve_configured_backend_and_cache_path(
    tmp_path,
) -> None:
    settings = preop._classifier_preop_settings(
        Settings(
            classifier_backend="custom-classifier",
            classifier_model_cache_path=tmp_path / "models",
        )
    )

    assert settings.classifier_backend == "custom-classifier"
    assert settings.classifier_model_cache_path == tmp_path / "models"
