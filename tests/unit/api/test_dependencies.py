from types import SimpleNamespace

from wild_catalog.api.dependencies import get_identify_pipeline, get_settings


def test_get_settings_is_cached(monkeypatch) -> None:
    calls = []

    class _Settings:
        @classmethod
        def from_env(cls):
            calls.append("called")
            return SimpleNamespace(marker="settings")

    monkeypatch.setattr("wild_catalog.api.dependencies.Settings", _Settings)
    get_settings.cache_clear()

    try:
        first = get_settings()
        second = get_settings()

        assert first.marker == "settings"
        assert second is first
        assert calls == ["called"]
    finally:
        get_settings.cache_clear()


def test_get_identify_pipeline_builds_pipeline(monkeypatch) -> None:
    settings = SimpleNamespace(marker="settings")
    conversion = SimpleNamespace(marker="conversion")
    wildlife_detector = SimpleNamespace(marker="wildlife_detector")

    monkeypatch.setattr("wild_catalog.api.dependencies.get_settings", lambda: settings)
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.ImageConversionService",
        lambda received_settings: conversion if received_settings is settings else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.WildlifeDetector",
        lambda: wildlife_detector,
    )

    pipeline = get_identify_pipeline()

    assert pipeline._settings is settings
    assert pipeline._conversion is conversion
    assert pipeline._wildlife_detector is wildlife_detector
