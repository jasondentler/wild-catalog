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

    first = get_settings()
    second = get_settings()

    assert first.marker == "settings"
    assert second is first
    assert calls == ["called"]


def test_get_identify_pipeline_builds_pipeline(monkeypatch) -> None:
    settings = SimpleNamespace(marker="settings")
    conversion = SimpleNamespace(marker="conversion")

    monkeypatch.setattr("wild_catalog.api.dependencies.get_settings", lambda: settings)
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.ImageConversionService",
        lambda received_settings: conversion if received_settings is settings else None,
    )

    pipeline = get_identify_pipeline()

    assert pipeline._settings is settings
    assert pipeline._conversion is conversion
