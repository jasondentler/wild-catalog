from dataclasses import replace
from pathlib import Path

from PIL import Image

from wild_catalog.classifier.registry import build_classifier
from wild_catalog.core.config import Settings

DEFAULT_CLASSIFIER_MODEL_CACHE_PATH = Path("data/models/classifier")


def preop_classifier_model(settings: Settings | None = None) -> None:
    settings = _classifier_preop_settings(settings or Settings.from_env())
    classifier = build_classifier(settings)

    classifier.predict_species(
        [
            Image.new("RGB", (224, 224), color=(128, 128, 128)),
        ]
    )


def _classifier_preop_settings(settings: Settings) -> Settings:
    return replace(
        settings,
        classifier_backend=(
            "birder-inat21"
            if settings.classifier_backend == "stub"
            else settings.classifier_backend
        ),
        classifier_model_cache_path=(
            settings.classifier_model_cache_path or DEFAULT_CLASSIFIER_MODEL_CACHE_PATH
        ),
    )


def main() -> None:
    preop_classifier_model()


if __name__ == "__main__":
    main()
