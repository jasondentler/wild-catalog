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
    settings = SimpleNamespace(
        marker="settings",
        logit_conditioning_gamma=2.0,
        logit_conditioning_epsilon=1e-12,
        species_classifier_top_k=5,
    )
    conversion = SimpleNamespace(marker="conversion")
    wildlife_detector = SimpleNamespace(marker="wildlife_detector", device="mps")
    detection_deduplicator = SimpleNamespace(marker="detection_deduplicator")
    image_cropper = SimpleNamespace(marker="image_cropper")
    species_classifier = SimpleNamespace(marker="species_classifier")
    expected_range_prior_service = SimpleNamespace(marker="range_prior_service")
    expected_logit_conditioner = SimpleNamespace(marker="logit_conditioner")
    detection_processing_pipeline = SimpleNamespace(
        marker="detection_processing_pipeline"
    )

    monkeypatch.setattr("wild_catalog.api.dependencies.get_settings", lambda: settings)
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.ImageConversionService",
        lambda received_settings: conversion if received_settings is settings else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.WildlifeDetector",
        lambda: wildlife_detector,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.DetectionDeduplicator",
        lambda: detection_deduplicator,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.ImageCropper",
        lambda received_settings: image_cropper if received_settings is settings else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.SpeciesClassifier",
        lambda received_settings, *, device: species_classifier
        if received_settings is settings and device == "mps"
        else None,
    )
    monkeypatch.setattr(
        "wild_catalog.api.dependencies.SpeciesRangePriorService",
        lambda received_settings: expected_range_prior_service
        if received_settings is settings
        else None,
    )

    def build_logit_conditioner(*, gamma, epsilon, top_k):
        if gamma == 2.0 and epsilon == 1e-12 and top_k == 5:
            return expected_logit_conditioner
        return None

    monkeypatch.setattr(
        "wild_catalog.api.dependencies.LogitConditioner",
        build_logit_conditioner,
    )

    def build_detection_processing_pipeline(
        received_cropper,
        received_classifier,
        *,
        range_prior_service: object,
        logit_conditioner: object,
    ):
        if (
            received_cropper is image_cropper
            and received_classifier is species_classifier
            and range_prior_service is expected_range_prior_service
            and logit_conditioner is expected_logit_conditioner
        ):
            return detection_processing_pipeline
        return None

    monkeypatch.setattr(
        "wild_catalog.api.dependencies.DetectionProcessingPipeline",
        build_detection_processing_pipeline,
    )

    get_identify_pipeline.cache_clear()

    try:
        pipeline = get_identify_pipeline()

        assert pipeline._settings is settings
        assert pipeline._conversion is conversion
        assert pipeline._wildlife_detector is wildlife_detector
        assert pipeline._detection_deduplicator is detection_deduplicator
        assert pipeline._detection_processing_pipeline is detection_processing_pipeline
    finally:
        get_identify_pipeline.cache_clear()
