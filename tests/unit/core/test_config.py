from pathlib import Path

import pytest

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
    assert settings.detection_iou_threshold == 0.45


def test_settings_from_env_reads_model_backends(monkeypatch) -> None:
    monkeypatch.setenv("WILD_CATALOG_DETECTOR_BACKEND", "grounding-dino")
    monkeypatch.setenv("WILD_CATALOG_CLASSIFIER_BACKEND", "birder-inat21")

    settings = Settings.from_env()

    assert settings.detector_backend == "grounding-dino"
    assert settings.classifier_backend == "birder-inat21"


def test_settings_from_env_reads_detection_iou_threshold(monkeypatch) -> None:
    monkeypatch.setenv("WILD_CATALOG_DETECTION_IOU_THRESHOLD", "0.5")

    settings = Settings.from_env()

    assert settings.detection_iou_threshold == 0.5


def test_settings_rejects_invalid_detection_iou_threshold() -> None:
    with pytest.raises(ValueError, match="detection_iou_threshold"):
        Settings(detection_iou_threshold=1.1)


def test_settings_from_env_reads_optional_path(monkeypatch) -> None:
    monkeypatch.setenv(
        "WILD_CATALOG_SPECIES_CLASSIFIER_MODEL_CACHE_PATH",
        "/tmp/model-cache",
    )

    settings = Settings.from_env()

    assert settings.classifier_model_cache_path == Path("/tmp/model-cache")


def test_settings_from_env_reads_range_map_builder_settings(monkeypatch) -> None:
    monkeypatch.setenv("WILD_CATALOG_INAT_RANGE_MAPS_METADATA_URL", "https://example.test/meta.json")
    monkeypatch.setenv("WILD_CATALOG_INAT_RANGE_MAPS_DOWNLOAD_DIR", "/tmp/range-downloads")
    monkeypatch.setenv("WILD_CATALOG_INAT_RANGE_MAPS_DOWNLOAD_CONCURRENCY", "8")
    monkeypatch.setenv("WILD_CATALOG_RANGE_MAP_STORE_PATH", "/tmp/ranges.sqlite3")
    monkeypatch.setenv("WILD_CATALOG_RANGE_MAP_H3_RESOLUTION", "7")
    monkeypatch.setenv("WILD_CATALOG_RANGE_PRIOR_CACHE_ENABLED", "false")
    monkeypatch.setenv("WILD_CATALOG_RANGE_PRIOR_CACHE_H3_RESOLUTION", "6")
    monkeypatch.setenv("WILD_CATALOG_RANGE_PRIOR_CACHE_MAX_ENTRIES", "123")

    settings = Settings.from_env()

    assert settings.inat_range_maps_metadata_url == "https://example.test/meta.json"
    assert settings.inat_range_maps_download_dir == Path("/tmp/range-downloads")
    assert settings.inat_range_maps_download_concurrency == 8
    assert settings.range_map_store_path == Path("/tmp/ranges.sqlite3")
    assert settings.range_map_h3_resolution == 7
    assert settings.range_prior_cache_enabled is False
    assert settings.range_prior_cache_h3_resolution == 6
    assert settings.range_prior_cache_max_entries == 123


def test_settings_from_env_defaults_range_map_store_path(monkeypatch) -> None:
    monkeypatch.delenv("WILD_CATALOG_RANGE_MAP_STORE_PATH", raising=False)

    settings = Settings.from_env()

    assert settings.range_map_store_path == Path("data/range-maps/ranges.sqlite3")
