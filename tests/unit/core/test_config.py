from pathlib import Path

from wild_catalog.core.config import Settings


def test_settings_defaults_to_development() -> None:
    assert Settings().env == "development"


def test_settings_from_env_uses_defaults(monkeypatch) -> None:
    monkeypatch.delenv("WILD_CATALOG_DETECTOR_BACKEND", raising=False)
    monkeypatch.delenv("WILD_CATALOG_CLASSIFIER_BACKEND", raising=False)

    settings = Settings.from_env()

    assert settings.detector_backend == "stub"
    assert settings.classifier_backend == "stub"
    assert settings.max_detections == 8
    assert settings.crop_margin_ratio == 0.12


def test_settings_from_env_reads_model_backends(monkeypatch) -> None:
    monkeypatch.setenv("WILD_CATALOG_DETECTOR_BACKEND", "grounding-dino")
    monkeypatch.setenv("WILD_CATALOG_CLASSIFIER_BACKEND", "birder-inat21")

    settings = Settings.from_env()

    assert settings.detector_backend == "grounding-dino"
    assert settings.classifier_backend == "birder-inat21"


def test_settings_from_env_reads_optional_path(monkeypatch) -> None:
    monkeypatch.setenv(
        "WILD_CATALOG_SPECIES_CLASSIFIER_MODEL_CACHE_PATH",
        "/tmp/model-cache",
    )

    settings = Settings.from_env()

    assert settings.classifier_model_cache_path == Path("/tmp/model-cache")
