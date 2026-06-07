from wild_catalog.api.dependencies import (
    clear_dependency_caches,
    get_identify_pipeline,
    get_settings,
)
from wild_catalog.core.config import Settings
from wild_catalog.pipeline.identify import IdentifyPipeline


def teardown_function() -> None:
    clear_dependency_caches()


def test_get_settings_returns_cached_settings(monkeypatch) -> None:
    monkeypatch.setenv("WILD_CATALOG_DETECTOR_BACKEND", "stub")

    first = get_settings()
    second = get_settings()

    assert isinstance(first, Settings)
    assert first is second


def test_get_identify_pipeline_returns_cached_pipeline(monkeypatch) -> None:
    monkeypatch.setenv("WILD_CATALOG_DETECTOR_BACKEND", "stub")
    monkeypatch.setenv("WILD_CATALOG_CLASSIFIER_BACKEND", "stub")

    first = get_identify_pipeline()
    second = get_identify_pipeline()

    assert isinstance(first, IdentifyPipeline)
    assert first is second


def test_clear_dependency_caches_allows_settings_reload(monkeypatch) -> None:
    monkeypatch.setenv("WILD_CATALOG_DETECTOR_BACKEND", "stub")

    first = get_settings()

    monkeypatch.setenv("WILD_CATALOG_DETECTOR_BACKEND", "changed")
    clear_dependency_caches()

    second = get_settings()

    assert first.detector_backend == "stub"
    assert second.detector_backend == "changed"
